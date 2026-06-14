"""Camada Bronze: ingestão da API para JSONL local.

Grava o dado CRU (sem transformação de negócio), só com colunas de auditoria.
A versão Databricks (notebooks/01_ingest_bronze.py) lê esses JSONL do Volume
e materializa como Delta.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from conf.config import ENDPOINTS, FANOUT_LIMITS, SAMPLES_DIR
from src.api import iter_pages, get_json


def _audit(endpoint, source_url):
    """Metadados de linhagem anexados a cada registro cru."""
    return {
        "ingest_ts": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "source_url": source_url,
    }


def collect_simple(name, max_pages=None):
    """Coleta um endpoint paginado simples e grava em JSONL."""
    cfg = ENDPOINTS[name]
    out = Path(SAMPLES_DIR) / f"{name}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with out.open("w", encoding="utf-8") as f:
        for records, _, source_url in iter_pages(cfg["path"], params=cfg["params"], max_pages=max_pages):
            for rec in records:
                rec["_audit"] = _audit(name, source_url)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
    return n, out


def _load_parents(parent_name, only_nominais=False):
    """Lê os IDs do JSONL do pai.

    Se only_nominais=True, mantém só votações com placar na descrição
    ("...Sim: X; Não: Y; Total: Z"), que são as que têm voto individual.
    """
    path = Path(SAMPLES_DIR) / f"{parent_name}.jsonl"
    if not path.exists():
        raise RuntimeError(
            f"pai '{parent_name}' não foi coletado ainda. "
            f"Rode collect_simple('{parent_name}') primeiro."
        )
    ids = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if "id" not in obj:
                continue
            if only_nominais and "Total:" not in (obj.get("descricao") or ""):
                continue                  # simbólica: sem voto individual, pula
            ids.append(obj["id"])
    return ids


def collect_fanout(name, max_parents=None):
    """Coleta um endpoint filho (depende do id do pai). Itera anos se configurado."""
    cfg = ENDPOINTS[name]
    parent_ids = _load_parents(cfg["fanout_from"], only_nominais=cfg.get("only_nominais", False))

    if max_parents is None:
        max_parents = FANOUT_LIMITS.get(name, 10)
    parent_ids = parent_ids[:max_parents]          # trava de volume

    anos = cfg.get("anos", [None])                 # [None] = roda 1x, sem filtro de ano

    out = Path(SAMPLES_DIR) / f"{name}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with out.open("w", encoding="utf-8") as f:
        for pid in parent_ids:
            path = cfg["path"].format(id=pid)
            for ano in anos:
                params = dict(cfg["params"])
                if ano is not None:
                    params["ano"] = ano
                try:
                    if cfg["paginated"]:
                        for records, _, source_url in iter_pages(path, params=params):
                            for rec in records:
                                rec["_parent_id"] = pid
                                rec["_audit"] = _audit(name, source_url)
                                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                                total += 1
                    else:
                        r = get_json(path, params=params)
                        records = r.json().get("dados", []) or []
                        if isinstance(records, dict):
                            records = [records]
                        for rec in records:
                            rec["_parent_id"] = pid
                            rec["_audit"] = _audit(name, r.url)
                            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                            total += 1
                except Exception as e:
                    print(f"[warn] {name} pid={pid} ano={ano}: {e}")
    return total, out


def collect_all(max_pages_simple=2):
    """Pipeline completo de coleta — usado pelo runner."""
    results = {}

    for name in ["partidos", "deputados", "frentes", "orgaos", "eventos", "votacoes"]:
        n, path = collect_simple(name, max_pages=max_pages_simple)
        results[name] = n
        print(f"  {name:<22s} {n:>5d} -> {path.name}")

    for name in ["frente_membros", "deputado_despesas", "evento_deputados", "votacao_votos"]:
        n, path = collect_fanout(name)
        results[name] = n
        print(f"  {name:<22s} {n:>5d} -> {path.name}")

    return results