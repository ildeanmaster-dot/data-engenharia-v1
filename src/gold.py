"""Gold: star schema + 6 entregaveis analiticos.

Fluxo:
  silver dict -> dim_* + fato_* -> gold_* (entregaveis)

Cada entregavel e uma funcao "build_*" que devolve um DataFrame pandas.
Em prod (Databricks) os DataFrames viram tabelas Delta no Volume.
"""
import pandas as pd


# ----------------------------------------------------------------------
# Dimensoes
# ----------------------------------------------------------------------

def dim_deputado(silver):
    df = silver["deputados"][[
        "id_deputado", "nome", "sigla_partido", "sigla_uf", "id_legislatura"
    ]].copy()
    return df


def dim_partido(silver):
    df = silver["partidos"][["id_partido", "sigla_partido", "nome_partido"]].copy()
    return df


def dim_frente(silver):
    df = silver["frentes"][["id_frente", "nome_frente", "id_legislatura"]].copy()
    return df


def dim_orgao(silver):
    df = silver["orgaos"][[
        "id_orgao", "sigla_orgao", "nome_orgao", "tipo_orgao", "cod_tipo_orgao"
    ]].copy()
    return df


def dim_evento(silver):
    df = silver["eventos"][[
        "id_evento", "data_hora_inicio", "data_hora_fim", "descricao_tipo", "situacao"
    ]].copy()
    return df


# ----------------------------------------------------------------------
# Fatos
# ----------------------------------------------------------------------

def fato_voto(silver):
    """Voto individual de cada deputado em cada votacao."""
    df = silver["votacao_votos"].copy()
    return df[["id_votacao", "id_deputado", "tipo_voto", "data_registro_voto"]]


def fato_presenca(silver):
    """Deputados que apareceram em cada evento."""
    df = silver["evento_deputados"].copy()
    return df[["id_evento", "id_deputado", "sigla_partido", "sigla_uf"]]


def fato_despesa(silver):
    """Despesas CEAP por deputado."""
    df = silver["deputado_despesas"].copy()
    cols = [
        "id_deputado", "ano", "mes", "tipo_despesa", "valor_liquido",
        "nome_fornecedor", "cnpj_fornecedor", "data_documento",
    ]
    cols = [c for c in cols if c in df.columns]
    return df[cols]
