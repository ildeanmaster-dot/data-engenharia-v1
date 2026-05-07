# Fast Track Engenharia — Câmara dos Deputados

Projeto final do programa Upskill Tiller (Engenharia de Dados, T2). A ideia
é construir um pipeline ponta-a-ponta sobre os dados abertos da Câmara dos
Deputados rodando no Databricks.

API: https://dadosabertos.camara.leg.br/

## O que tem aqui

Um pipeline simples em três camadas:

- **Bronze** — JSON cru da API, salvo como JSONL local + Delta no Databricks
- **Silver** — limpeza, tipos, dedup
- **Gold** — dimensões + fatos + 6 entregáveis analíticos

Os 6 entregáveis pedidos no desafio:

1. Atlas das frentes parlamentares (HHI por frente)
2. Calendário de eventos com taxa de presença
3. Correlação entre frentes e votações
4. Raio-X CEAP — top de gastos por categoria
5. Auditoria de CPIs
6. Score de engajamento parlamentar

## Como rodar local

```bash
python -m venv .venv
.venv\Scripts\activate  # ou source .venv/bin/activate no linux
pip install -r requirements.txt
python -m src.runner
```

A primeira execução vai baixar amostras da API e gerar parquets em `data/gold/`.

Se ja tem os JSONL coletados (em `data/samples/`), pode pular a coleta:

```bash
python -m src.runner --skip-bronze
```

### Rodar os tests

```bash
python -m pytest tests/ -v
```

## No Databricks

Tem 3 notebooks na pasta `notebooks/`:

- `01_ingest_bronze.py` — coleta da API e grava em Volume UC
- `02_silver_gold.py` — transforma e materializa Gold
- `03_analytics.py` — queries SQL com os 6 entregáveis

Importar via Repos (Git folder) e rodar em ordem.

## Estrutura

```
.
├── conf/config.py              # endpoints da API
├── src/
│   ├── api.py                  # cliente HTTP
│   ├── bronze.py               # ingestão
│   ├── silver.py               # transforms
│   ├── gold.py                 # star schema + entregáveis
│   └── runner.py               # pipeline local
├── notebooks/                  # versão Databricks
└── tests/                      # smoke tests
```

## Decisões rápidas

- **JSONL local antes de Delta** — facilita debug sem subir Spark toda hora
- **Sem catálogo YAML** — endpoints como dict Python é mais direto pra esse volume
- **PySpark só no Databricks** — local roda em pandas, é mais rápido pra iterar

## Sobre ingestão fora do cluster

Em arquiteturas reais a coleta da API roda separada do cluster Databricks
(Lambda/Airflow/Cron entrega no object storage; cluster consome dali).
Vantagens: cluster fica focado em processamento pesado, ingestão não paga
compute parado, segurança fica granular. O `scripts/live_demo.py` reproduz
esse fluxo numa demo: bate na API local, sobe pro Volume, dispara
notebooks no Databricks.

Feito com auxílio de IA (Claude). Decisões e revisões são minhas.
