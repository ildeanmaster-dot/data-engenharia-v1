"""Ponto de entrada do pipeline local.

Uso:
    python -m src.runner                 # coleta a Bronze (volume reduzido)
    python -m src.runner --skip-bronze   # pula a coleta (usa JSONL já existente)
    python -m src.runner --max-pages 5   # mais páginas por endpoint simples
"""
import argparse
import logging
import time

from src.bronze import collect_all


def _parse_args():
    p = argparse.ArgumentParser(description="Pipeline Câmara dos Deputados (local).")
    p.add_argument("--skip-bronze", action="store_true",
                   help="não coleta da API; assume que os JSONL já existem em data/samples/")
    p.add_argument("--max-pages", type=int, default=2,
                   help="páginas por endpoint simples na Bronze (default: 2)")
    return p.parse_args()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = _parse_args()

    if args.skip_bronze:
        print("== Bronze: pulada (--skip-bronze) ==")
    else:
        print("== Bronze: coletando da API ==")
        t0 = time.time()
        results = collect_all(max_pages_simple=args.max_pages)
        total = sum(results.values())
        print(f"== Bronze concluída: {total} registros em {time.time() - t0:.1f}s ==")

    # Blocos 2–4 vão plugar aqui:
    #   from src.silver import to_silver_all
    #   from src.gold import build_all
    print("Pipeline finalizado.")


if __name__ == "__main__":
    main()