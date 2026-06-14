"""Tests da camada silver - rename, dedup, parse de datas."""
import json
from pathlib import Path

import pytest

from src.silver import to_silver
from conf import config


@pytest.fixture
def fake_samples(tmp_path, monkeypatch):
    """Cria um data/samples mockado num tmpdir."""
    monkeypatch.setattr(config, "SAMPLES_DIR", str(tmp_path))
    # tambem precisa atualizar a referencia em silver
    import src.silver as silver_mod
    monkeypatch.setattr(silver_mod, "SAMPLES_DIR", str(tmp_path))
    return tmp_path


def _write(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_silver_deputados_rename(fake_samples):
    _write(fake_samples / "deputados.jsonl", [
        {"id": 1, "nome": "A", "siglaPartido": "PT", "siglaUf": "SP", "idLegislatura": 57},
        {"id": 2, "nome": "B", "siglaPartido": "PL", "siglaUf": "RJ", "idLegislatura": 57},
    ])
    df = to_silver("deputados")
    assert "id_deputado" in df.columns
    assert "sigla_partido" in df.columns
    assert "sigla_uf" in df.columns
    assert len(df) == 2


def test_silver_dedup_pk(fake_samples):
    # mesmo id_deputado 2x - deve manter so 1
    _write(fake_samples / "deputados.jsonl", [
        {"id": 1, "nome": "A", "siglaPartido": "PT", "siglaUf": "SP", "idLegislatura": 57},
        {"id": 1, "nome": "A", "siglaPartido": "PT", "siglaUf": "SP", "idLegislatura": 57},
    ])
    df = to_silver("deputados")
    assert len(df) == 1


def test_silver_eventos_parse_timestamp(fake_samples):
    _write(fake_samples / "eventos.jsonl", [
        {"id": 100, "dataHoraInicio": "2025-03-15T10:00", "dataHoraFim": "2025-03-15T12:00",
         "descricaoTipo": "Audiencia", "situacao": "Encerrado"},
    ])
    df = to_silver("eventos")
    assert df["data_hora_inicio"].dtype.name.startswith("datetime")
