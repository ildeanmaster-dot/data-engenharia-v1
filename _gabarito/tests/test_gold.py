"""Tests dos entregaveis gold com dados sinteticos pequenos."""
import pandas as pd
import pytest

from src.gold import (
    gold_atlas_frentes,
    gold_frente_diversidade_hhi,
    gold_alinhamento_frente_vs_partido,
    gold_ceap_top_por_categoria,
    gold_engajamento_deputado,
)


@pytest.fixture
def silver_min():
    """Silver minimo com dados consistentes pros 3 entregaveis testados aqui."""
    deputados = pd.DataFrame([
        {"id_deputado": 1, "nome": "A", "sigla_partido": "PT", "sigla_uf": "SP", "id_legislatura": 57},
        {"id_deputado": 2, "nome": "B", "sigla_partido": "PT", "sigla_uf": "SP", "id_legislatura": 57},
        {"id_deputado": 3, "nome": "C", "sigla_partido": "PL", "sigla_uf": "RJ", "id_legislatura": 57},
    ])
    frentes = pd.DataFrame([
        {"id_frente": 10, "nome_frente": "F1", "id_legislatura": 57},
        {"id_frente": 20, "nome_frente": "F2", "id_legislatura": 57},
    ])
    frente_membros = pd.DataFrame([
        {"id_frente": 10, "id_deputado": 1},
        {"id_frente": 10, "id_deputado": 2},
        {"id_frente": 10, "id_deputado": 3},
        {"id_frente": 20, "id_deputado": 1},
    ])
    votos = pd.DataFrame([
        {"id_votacao": 100, "id_deputado": 1, "tipo_voto": "Sim", "sigla_partido": "PT", "data_registro_voto": None},
        {"id_votacao": 100, "id_deputado": 2, "tipo_voto": "Sim", "sigla_partido": "PT", "data_registro_voto": None},
        {"id_votacao": 100, "id_deputado": 3, "tipo_voto": "Nao", "sigla_partido": "PL", "data_registro_voto": None},
    ])
    eventos = pd.DataFrame([{"id_evento": 1}])
    evento_dep = pd.DataFrame([
        {"id_evento": 1, "id_deputado": 1, "sigla_partido": "PT", "sigla_uf": "SP"},
        {"id_evento": 1, "id_deputado": 2, "sigla_partido": "PT", "sigla_uf": "SP"},
    ])
    despesas = pd.DataFrame([
        {"id_deputado": 1, "ano": 2024, "mes": 1, "tipo_despesa": "COMBUSTIVEIS", "valor_liquido": 100.0,
         "nome_fornecedor": "F1", "cnpj_fornecedor": "00000000000001", "data_documento": None,
         "cod_documento": "D1"},
        {"id_deputado": 2, "ano": 2024, "mes": 1, "tipo_despesa": "COMBUSTIVEIS", "valor_liquido": 5000.0,
         "nome_fornecedor": "F2", "cnpj_fornecedor": "00000000000002", "data_documento": None,
         "cod_documento": "D2"},
    ])
    return {
        "deputados": deputados,
        "frentes": frentes,
        "frente_membros": frente_membros,
        "votacao_votos": votos,
        "eventos": eventos,
        "evento_deputados": evento_dep,
        "deputado_despesas": despesas,
    }


def test_atlas_e_hhi(silver_min):
    atlas = gold_atlas_frentes(silver_min)
    assert len(atlas) == 4

    hhi = gold_frente_diversidade_hhi(atlas)
    # F1 tem 2 PT + 1 PL -> hhi = (2/3)^2 + (1/3)^2 = 0.555...
    f1 = hhi[hhi["id_frente"] == 10].iloc[0]
    assert abs(f1["hhi"] - 5/9) < 1e-6
    # F2 tem 1 PT -> hhi = 1.0
    f2 = hhi[hhi["id_frente"] == 20].iloc[0]
    assert f2["hhi"] == 1.0


def test_alinhamento_frente_vs_partido(silver_min):
    resumo_f, resumo_p = gold_alinhamento_frente_vs_partido(silver_min)
    # PT votou unanime Sim -> alinhamento 1.0
    pt = resumo_p[resumo_p["sigla_partido"] == "PT"].iloc[0]
    assert pt["alinhamento_medio"] == 1.0


def test_ceap_top_n(silver_min):
    out = gold_ceap_top_por_categoria(silver_min, top_n=2)
    assert len(out) == 2
    # o de maior valor (5000) deve aparecer com rank 1
    top = out.sort_values("rank").iloc[0]
    assert top["valor_liquido"] == 5000.0


def test_engajamento_normalizado(silver_min):
    out = gold_engajamento_deputado(silver_min)
    # deve ter 3 deputados
    assert len(out) == 3
    # engajamento deve estar entre 0 e 1
    assert out["engajamento"].between(0, 1).all()
