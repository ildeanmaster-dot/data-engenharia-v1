"""Demo end-to-end ao vivo para apresentacao.

Faz tudo num comando:
1. apaga samples antigos (zera estado)
2. coleta da API da Camara (bate na API real, ao vivo)
3. sobe os JSONL recem coletados pro Volume Databricks
4. dispara os notebooks Bronze->Silver->Gold->Analytics como Job
5. valida a Gold materializada via SQL e imprime contagens

Uso:
    python scripts/live_demo.py

Requer DATABRICKS_HOST e DATABRICKS_TOKEN no .env.

Por que ingestao fica fora do cluster Databricks?
    Clusters Databricks (especialmente serverless / Free Edition) tem egress
    de internet restrito por seguranca. Em arquiteturas reais, a ingestao
    da API fica em worker dedicado (Lambda, Cron, Airflow) que entrega
    JSONL no object storage. O cluster consome dali. Esse script reproduz
    esse padrao.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent

# config Databricks
SCHEMA = "ftkeng_v1"
WORKSPACE_REPO = "/Workspace/Users/developer@yottaflow.com.br/FAST-TRACK-ENGENHARIA-V1"
NOTEBOOKS = [
    f"{WORKSPACE_REPO}/notebooks/01_ingest_bronze",
    f"{WORKSPACE_REPO}/notebooks/02_silver_gold",
    f"{WORKSPACE_REPO}/notebooks/03_analytics",
]


def _load_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        sys.exit("ERRO: .env nao encontrado. Crie com DATABRICKS_HOST e DATABRICKS_TOKEN.")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")


def _h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def step1_limpa_samples():
    print("\n[1/5] Limpando samples antigos...")
    samples_dir = ROOT / "data" / "samples"
    if samples_dir.exists():
        shutil.rmtree(samples_dir)
    samples_dir.mkdir(parents=True, exist_ok=True)
    print(f"  apagados. {samples_dir} limpo.")


def step2_coleta_api():
    print("\n[2/5] Coletando da API ao vivo (isso vai aparecer no terminal)...")
    sys.path.insert(0, str(ROOT))
    from src.bronze import collect_all
    results = collect_all(max_pages_simple=2)
    total = sum(results.values())
    print(f"\n  Total: {total} registros em {len(results)} entidades")
    return results


def step3_upload_volume(host, token):
    print(f"\n[3/5] Subindo JSONL para /Volumes/workspace/{SCHEMA}/lakehouse/samples/...")
    base = f"/Workspace/Users/developer@yottaflow.com.br/FAST-TRACK-ENGENHARIA-V1/data/samples"
    samples = sorted((ROOT / "data" / "samples").glob("*.jsonl"))
    H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for f in samples:
        content = f.read_bytes()
        if not content:
            continue
        r = requests.post(
            f"{host}/api/2.0/workspace/import",
            headers=H,
            json={"path": f"{base}/{f.name}",
                  "content": base64.b64encode(content).decode(),
                  "format": "AUTO", "overwrite": True},
            timeout=120,
        )
        status = "ok" if r.status_code == 200 else f"FAIL {r.status_code}"
        print(f"  {status:<10s} {f.name:<32s} {len(content):>9d} B")


def step4_run_pipeline(host, token):
    print(f"\n[4/5] Disparando pipeline no Databricks (schema {SCHEMA})...")
    H = _h(token)
    tasks = []
    prev = None
    for nb_path in NOTEBOOKS:
        key = nb_path.rsplit("/", 1)[-1]
        task = {"task_key": key, "notebook_task": {"notebook_path": nb_path}}
        if prev:
            task["depends_on"] = [{"task_key": prev}]
        tasks.append(task)
        prev = key

    body = {"run_name": f"ftk-v1-live-demo-{int(time.time())}", "tasks": tasks}
    r = requests.post(f"{host}/api/2.2/jobs/runs/submit", headers=H,
                      data=json.dumps(body), timeout=60)
    run_id = r.json().get("run_id")
    print(f"  run_id={run_id}")

    deadline = time.time() + 60 * 30
    while True:
        if time.time() > deadline:
            print("  timeout 30 min")
            return False
        time.sleep(20)
        st = requests.get(f"{host}/api/2.2/jobs/runs/get?run_id={run_id}",
                          headers=H, timeout=60).json()
        life = st.get("state", {}).get("life_cycle_state")
        result = st.get("state", {}).get("result_state")
        print(f"  life={life} result={result}")
        if life in ("TERMINATED", "INTERNAL_ERROR", "SKIPPED"):
            for t in st.get("tasks", []):
                tk = t["task_key"]
                tr = t.get("state", {}).get("result_state")
                print(f"    task={tk:<22s} state={tr}")
            return result == "SUCCESS"


def step5_validar_gold(host, token):
    print(f"\n[5/5] Validando Gold...")
    H = _h(token)
    r = requests.get(f"{host}/api/2.0/sql/warehouses", headers=H, timeout=30).json()
    if not r.get("warehouses"):
        print("  nenhum warehouse SQL disponivel")
        return
    wid = r["warehouses"][0]["id"]

    queries = [
        ("gold_atlas_frentes", "id_frente, nome_frente, sigla_partido, sigla_uf"),
        ("gold_frente_diversidade", "*"),
        ("gold_ceap_top_categoria", "*"),
        ("gold_engajamento", "id_deputado, nome, sigla_partido, engajamento, percentil"),
    ]
    for tabela, _ in queries:
        sql = f"SELECT COUNT(*) AS n FROM delta.`/Volumes/workspace/{SCHEMA}/lakehouse/gold/{tabela}`"
        body = {"statement": sql, "warehouse_id": wid,
                "wait_timeout": "30s", "on_wait_timeout": "CONTINUE"}
        rsp = requests.post(f"{host}/api/2.0/sql/statements", headers=H,
                            data=json.dumps(body), timeout=60).json()
        sid = rsp.get("statement_id")
        state = rsp.get("status", {}).get("state")
        while state in ("PENDING", "RUNNING"):
            time.sleep(2)
            rsp = requests.get(f"{host}/api/2.0/sql/statements/{sid}",
                               headers=H, timeout=30).json()
            state = rsp.get("status", {}).get("state")
        if state == "SUCCEEDED":
            n = int(rsp["result"]["data_array"][0][0])
            print(f"  {tabela:<35s} {n:>6d} rows")
        else:
            err = rsp.get("status", {}).get("error", {}).get("message", "?")
            print(f"  {tabela:<35s} ERRO: {err[:100]}")


def main():
    _load_env()
    host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
    token = os.environ.get("DATABRICKS_TOKEN", "")
    if not host or not token:
        sys.exit("DATABRICKS_HOST/TOKEN ausentes em .env")

    print("=" * 60)
    print("LIVE DEMO — V1")
    print("API: https://dadosabertos.camara.leg.br/api/v2")
    print(f"Databricks schema: workspace.{SCHEMA}")
    print("=" * 60)

    step1_limpa_samples()
    step2_coleta_api()
    step3_upload_volume(host, token)
    ok = step4_run_pipeline(host, token)
    if ok:
        step5_validar_gold(host, token)
    print("\n=== Demo concluida ===")


if __name__ == "__main__":
    main()
