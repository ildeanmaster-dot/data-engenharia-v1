"""Catálogo dos endpoints da API da Câmara dos Deputados que vamos coletar.

Mantido como dict Python (em vez de YAML) para ter tab-complete no editor
e não depender de parser externo para esse volume.
Princípio: "configuração como dado" — adicionar uma fonte é editar o dict,
não a lógica de coleta (que vive em src/).
API base: https://dadosabertos.camara.leg.br/api/v2
"""
from datetime import datetime

# Anos de despesas (CEAP) a coletar. A 57a legislatura começou em 2023
# (deputados eleitos em out/2022), então cobrimos 2023 até o ano corrente.
# Dinâmico de propósito: evita hardcode que "para no tempo".
ANOS_CEAP = list(range(2023, datetime.now().year + 1))   # ex.: [2023, 2024, 2025, 2026]

# Onde gravar o JSONL cru da camada Bronze (local).
SAMPLES_DIR = "data/samples"


ENDPOINTS = {
    # ---- listas base (fontes independentes, paginadas) ----
    "deputados": {
        "path": "/deputados",
        "params": {"itens": 100, "ordem": "ASC", "ordenarPor": "nome"},
        "paginated": True,
    },
    "partidos": {
        "path": "/partidos",
        "params": {"itens": 100},
        "paginated": True,
    },
    "frentes": {
        "path": "/frentes",
        "params": {"idLegislatura": 57, "itens": 100},   # 57a legislatura (eleita em 2022)
        "paginated": True,
    },
    "orgaos": {
        "path": "/orgaos",
        "params": {"itens": 100},
        "paginated": True,
    },
    "eventos": {
        "path": "/eventos",
        "params": {"itens": 100},
        "paginated": True,
    },
    "votacoes": {
        "path": "/votacoes",
        "params": {"idOrgao": 180, "ordem": "DESC", "ordenarPor": "dataHoraRegistro", "itens": 100},
        "paginated": True,                # idOrgao 180 = Plenário (onde há votação nominal)
    },

    # ---- fan-outs (precisam do id de um pai já coletado) ----
    "frente_membros": {
        "path": "/frentes/{id}/membros",
        "params": {},
        "paginated": False,
        "fanout_from": "frentes",          # para cada frente, busca os membros
    },
    "deputado_despesas": {
        "path": "/deputados/{id}/despesas",
        "params": {"itens": 100, "ordem": "DESC", "ordenarPor": "ano"},
        "paginated": True,
        "fanout_from": "deputados",        # para cada deputado, busca as despesas
        "anos": ANOS_CEAP,                 # itera estes anos (carga por ano)
    },
    "evento_deputados": {
        "path": "/eventos/{id}/deputados",
        "params": {},
        "paginated": False,
        "fanout_from": "eventos",          # presença: quem esteve em cada evento
    },
    "votacao_votos": {
        "path": "/votacoes/{id}/votos",
        "params": {},
        "paginated": False,
        "fanout_from": "votacoes",
        "only_nominais": True,            # votos individuais só existem em votação nominal
    },
}

# Tetos para o fan-out não explodir o tempo de coleta enquanto aprendemos.
# Quando for rodar a coleta cheia, aumente ou remova estes limites.
FANOUT_LIMITS = {
    "frente_membros":    30,   # 30 frentes   x ~30 membros   ≈   900 registros
    "deputado_despesas": 20,   # 20 deputados x 4 anos x ~50  ≈ 4.000 registros
    "evento_deputados":  10,   # 10 eventos   x ~10 presentes ≈   100 registros
    # em FANOUT_LIMITS:
    "votacao_votos":     40,   # 40 votações nominais (após filtro) x ~470 votos ≈ 18.000
}