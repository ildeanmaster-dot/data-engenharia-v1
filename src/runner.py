"""Ponto de entrada do pipeline local.

Uso:
    python -m src.runner                 # coleta a Bronze (volume reduzido)
    python -m src.runner --skip-bronze   # pula a coleta (usa JSONL já existente)
    python -m src.runner --max-pages 5   # mais páginas por endpoint simples
"""
import argparse
import logging
import time
from pathlib import Path

from src.bronze import collect_all
from src.silver import to_silver_all
from src.gold import build_all

GOLD_DIR = "data/gold"


def _parse_args():
    p = argparse.ArgumentParser(description="Pipeline Câmara dos Deputados (local).")
    p.add_argument("--skip-bronze", action="store_true",
                   help="não coleta da API; assume que os JSONL já existem em data/samples/")
    p.add_argument("--max-pages", type=int, default=2,
                   help="páginas por endpoint simples na Bronze (default: 2)")
    return p.parse_args()


def save_tables(tables, out_dir=GOLD_DIR):
    """Materializa cada DataFrame Gold como Parquet (equivalente local ao Delta)."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(Path(out_dir) / f"{name}.parquet", index=False)
    return len(tables)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = _parse_args()

    # --- BRONZE ---
    if args.skip_bronze:
        print("== Bronze: pulada (--skip-bronze) ==")
    else:
        print("== Bronze: coletando da API ==")
        t0 = time.time()
        results = collect_all(max_pages_simple=args.max_pages)
        print(f"== Bronze concluída: {sum(results.values())} registros em {time.time() - t0:.1f}s ==")

    # --- SILVER ---
    print("== Silver: limpando e tipando ==")
    silver = to_silver_all()
    print(f"== Silver: {len(silver)} entidades ==")

    # --- GOLD ---
    print("== Gold: montando star schema + entregáveis ==")
    gold = build_all(silver)
    n = save_tables(gold)
    print(f"== Gold: {n} tabelas materializadas em {GOLD_DIR}/ ==")

    print("Pipeline finalizado.")


if __name__ == "__main__":
    main()