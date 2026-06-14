"""Pipeline local: bronze (API -> JSONL) -> silver (pandas) -> gold (pandas).

Uso:
    python -m src.runner

Salva os parquets resultantes em data/gold/.
"""
import os
import sys
from pathlib import Path

import pandas as pd

from src.bronze import collect_all
from src.silver import to_silver_all
from src import gold


def _save_parquet(df, path):
    if df is None or df.empty:
        print(f"  [skip] {path.name} (vazio)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    print(f"  [ok]   {path.name:<40s} {len(df):>5d} linhas")


def main(skip_bronze=False):
    out_dir = Path("data/gold")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not skip_bronze:
        print("\n=== Bronze (coleta da API) ===")
        results = collect_all(max_pages_simple=2)
        total = sum(results.values())
        print(f"\nTotal: {total} registros em {len(results)} entidades")

    print("\n=== Silver ===")
    silver = to_silver_all()
    for name, df in silver.items():
        print(f"  {name:<22s} {len(df):>5d}")

    print("\n=== Gold - dimensoes e fatos ===")
    _save_parquet(gold.dim_deputado(silver), out_dir / "dim_deputado.parquet")
    _save_parquet(gold.dim_partido(silver), out_dir / "dim_partido.parquet")
    _save_parquet(gold.dim_frente(silver), out_dir / "dim_frente.parquet")
    _save_parquet(gold.dim_orgao(silver), out_dir / "dim_orgao.parquet")
    _save_parquet(gold.dim_evento(silver), out_dir / "dim_evento.parquet")
    _save_parquet(gold.fato_voto(silver), out_dir / "fato_voto.parquet")
    _save_parquet(gold.fato_presenca(silver), out_dir / "fato_presenca.parquet")
    _save_parquet(gold.fato_despesa(silver), out_dir / "fato_despesa.parquet")

    print("\n=== Gold - entregaveis ===")
    atlas = gold.gold_atlas_frentes(silver)
    _save_parquet(atlas, out_dir / "gold_atlas_frentes.parquet")
    _save_parquet(gold.gold_frente_diversidade_hhi(atlas), out_dir / "gold_frente_diversidade.parquet")
    _save_parquet(gold.gold_deputados_em_n_frentes(atlas), out_dir / "gold_deputado_em_n_frentes.parquet")

    _save_parquet(gold.gold_taxa_presenca(silver), out_dir / "gold_taxa_presenca.parquet")
    _save_parquet(gold.gold_densidade_semanal(silver), out_dir / "gold_densidade_semanal.parquet")
    _save_parquet(gold.gold_eventos_futuros(silver), out_dir / "gold_eventos_futuros.parquet")

    resumo_frente, resumo_partido = gold.gold_alinhamento_frente_vs_partido(silver)
    _save_parquet(resumo_frente, out_dir / "gold_alinhamento_frente.parquet")
    _save_parquet(resumo_partido, out_dir / "gold_alinhamento_partido.parquet")

    _save_parquet(gold.gold_ceap_top_por_categoria(silver), out_dir / "gold_ceap_top_categoria.parquet")
    _save_parquet(gold.gold_ceap_ranking_fornecedor(silver), out_dir / "gold_ceap_ranking_fornecedor.parquet")
    _save_parquet(gold.gold_ceap_mensal_partido(silver), out_dir / "gold_ceap_mensal_partido.parquet")

    _save_parquet(gold.gold_cpis(silver), out_dir / "gold_cpis.parquet")

    _save_parquet(gold.gold_engajamento_deputado(silver), out_dir / "gold_engajamento.parquet")
    _save_parquet(gold.gold_absenteismo_votacao(silver), out_dir / "gold_absenteismo.parquet")

    print(f"\nFinalizado. Resultados em {out_dir.resolve()}")


if __name__ == "__main__":
    skip = "--skip-bronze" in sys.argv
    main(skip_bronze=skip)
