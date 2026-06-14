# Unity Catalog & Volumes

## Namespace de 3 níveis
`catalogo.schema.tabela` — ex.: `workspace.bronze.deputados`.
- **Catálogo:** topo da governança (no Free Edition: `workspace`).
- **Schema** (database): agrupa tabelas/volumes. No medalhão: `bronze`, `silver`, `gold`.
- **Tabela / View / Volume:** os objetos.

```sql
CREATE CATALOG IF NOT EXISTS meu_cat;          -- (em edições com permissão)
CREATE SCHEMA  IF NOT EXISTS workspace.bronze;
USE CATALOG workspace; USE SCHEMA bronze;
```

## Tabelas managed vs external
- **Managed (padrão e recomendado):** o UC controla storage, layout e otimização
  (auto compaction, etc.). Menor custo operacional.
  ```python
  df.write.saveAsTable("workspace.silver.deputados")          # cria/append
  df.write.mode("overwrite").option("overwriteSchema","true") \
    .saveAsTable("workspace.silver.deputados")                # sobrescreve
  df.writeTo("workspace.silver.deputados").createOrReplace()  # API moderna
  ```
- **External:** você aponta um `LOCATION` externo. Use só quando há requisito de
  storage próprio/compartilhamento fora do UC.

## Volumes (arquivos governados)
Para dados **não-tabulares** (JSON, CSV, imagens, modelos). Caminho POSIX:
`/Volumes/<catalogo>/<schema>/<volume>/...`
```python
spark.sql("CREATE VOLUME IF NOT EXISTS workspace.bronze.raw")
dbutils.fs.mkdirs("/Volumes/workspace/bronze/raw/samples")
df = spark.read.json("/Volumes/workspace/bronze/raw/samples/deputados.jsonl")
```
- Use Volume como **landing zone** do dado cru antes de virar Delta.
- Tabela e Volume não podem ocupar o mesmo path.

## Linhagem e governança
O UC registra **lineage** (origem/coluna), permissões (`GRANT`), e histórico.
É o que dá rastreabilidade exigida em ambientes regulados — combine com os
campos de auditoria da Bronze (`ingest_ts`, `source_url`).

## dbutils úteis
- `dbutils.fs.ls(path)` / `mkdirs` / `cp` / `rm` — sistema de arquivos.
- `dbutils.widgets` — parâmetros de notebook.
- `dbutils.notebook.run(...)` — orquestrar notebooks.
