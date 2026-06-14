---
name: databricks-eng-dados
description: >
  Especialista em Databricks para Engenharia de Dados, baseado na documentação
  oficial (docs.databricks.com, 2026). Use esta skill SEMPRE que o usuário
  trabalhar com Databricks: Unity Catalog (catálogo/schema/tabela, Volumes),
  Delta Lake (ACID, Time Travel, MERGE, OPTIMIZE, schema evolution), PySpark
  (DataFrame API, selectExpr, joins, window), notebooks, arquitetura medalhão
  (bronze/silver/gold) em Delta, Lakeflow Declarative Pipelines (ex-DLT) e
  expectations de qualidade, Jobs/Workflows, Auto Loader, carga incremental,
  Free Edition serverless, dbutils, ou ao portar um pipeline pandas para PySpark.
---

# Databricks para Engenharia de Dados

Guia operacional baseado na documentação oficial (2026). Use para escolher a
abordagem certa em Unity Catalog, Delta, PySpark e pipelines.

## Fatos essenciais (decore)

- **Unity Catalog (UC)** organiza tudo em 3 níveis: `catalogo.schema.tabela`.
  No **Free Edition** o catálogo padrão é `workspace`.
- **Volumes** = armazenamento governado para **arquivos** (não-tabelas). Caminho:
  `/Volumes/<catalogo>/<schema>/<volume>/...`. É onde dados crus "pousam".
- **Delta Lake** é o formato padrão de tabela (Parquet + log de transações).
  Toda tabela criada no Databricks é Delta por padrão.
- **Tabela managed** é o tipo **padrão e recomendado** — o UC gerencia storage,
  layout e otimização. Crie com `df.write.saveAsTable("cat.schema.tab")` ou
  `df.writeTo("cat.schema.tab").createOrReplace()`. Evite caminhos externos
  salvo necessidade real.
- **Free Edition** é **serverless** (sem cluster customizado, sem GPU); suporta
  SQL, Python, notebooks, Dashboards, Genie, **Lakeflow Declarative Pipelines**.
- Em notebooks, `spark` e `dbutils` já existem no escopo. Não instancie SparkSession.

## Mudanças de nome (2025/2026) — importante

| Nome novo (use este) | Nome antigo |
|---|---|
| **Lakeflow Spark Declarative Pipelines** (LDP) | Delta Live Tables (DLT) |
| **Lakeflow Jobs** | Databricks Jobs / Workflows |
| **Lakeflow Connect** | (ingestão gerenciada) |

A sintaxe de pipeline (`@dlt.table`, `CREATE STREAMING TABLE`, expectations)
permanece compatível; só o nome do produto mudou.

## Arquitetura medalhão em Delta (o padrão do projeto)

```
Volume (raw JSONL)  ->  bronze.<t>  ->  silver.<t>  ->  gold.<t>
   landing de arquivo     Delta cru      Delta limpo     Delta modelado
```
- Um schema por camada (`bronze`, `silver`, `gold`) sob o catálogo.
- Leia com `spark.read.json(path)` / `spark.table(...)`; grave com `saveAsTable`.

## PySpark x pandas (ao portar)

| pandas | PySpark |
|---|---|
| `pd.read_json` | `spark.read.json(path)` |
| `df.rename(columns=...)` | `df.selectExpr("a as b", ...)` |
| `df.drop_duplicates(subset=k)` | `df.dropDuplicates(k)` |
| `df.merge(o, on=k, how="left")` | `df.join(o, k, "left")` |
| `df.groupby(k).agg(...)` | `df.groupBy(k).agg(F.sum(...), ...)` |
| `pd.to_datetime` | `to_timestamp(col)` / `to_date(col)` |
| salvar parquet | `df.write.format("delta").saveAsTable(...)` |

> A lógica é a mesma; a engine muda. PySpark distribui e escala; pandas cabe na
> RAM de uma máquina. Use local para prototipar, Databricks para produzir.

## Quando usar o quê (decisão rápida)

- Gravar tabela de qualquer camada → `saveAsTable` (managed, é o padrão).
- Atualizar/UPSERT (incremental, SCD2) → **Delta `MERGE INTO`**.
- Reprocessar/auditar estado passado → **Time Travel** (`VERSION AS OF` / `TIMESTAMP AS OF`).
- Qualidade declarativa no pipeline → **expectations** (LDP/ex-DLT).
- Ingestão incremental de arquivos novos → **Auto Loader** (`cloudFiles`).
- Compactar arquivos pequenos / acelerar leitura → `OPTIMIZE` (+ `ZORDER BY`).

> Detalhes: `references/unity-catalog.md`, `references/delta.md`,
> `references/pyspark-patterns.md`, `references/lakeflow-expectations.md`.

## Armadilhas conhecidas

- **`overwriteSchema=true`** ao sobrescrever tabela cujo schema inferido muda
  entre execuções (comum lendo JSON da API).
- Campo **aninhado** no JSON acessa-se com ponto no `selectExpr`:
  `"deputado_.id as id_deputado"`.
- `display(df)` só funciona em notebook; em script use `df.show()`.
- No Free Edition não há cluster "all-purpose" clássico — use **serverless**;
  algumas libs/GPU não estão disponíveis.
- Tabela e Volume **não podem ocupar o mesmo caminho** (governança UC).
