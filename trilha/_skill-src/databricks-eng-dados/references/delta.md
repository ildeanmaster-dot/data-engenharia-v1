# Delta Lake — operações essenciais

Delta = Parquet + log de transações (`_delta_log`). Dá ACID, Time Travel, MERGE,
schema evolution e otimização. É o formato padrão de tabela no Databricks.

## Escrita
```python
df.write.format("delta").mode("overwrite") \
  .option("overwriteSchema", "true").saveAsTable("workspace.bronze.deputados")
# modos: append | overwrite | ignore | error
```

## MERGE (UPSERT) — base de carga incremental e SCD2
```sql
MERGE INTO silver.proposicoes AS t
USING staging_updates AS s
ON t.id = s.id
WHEN MATCHED AND t.hash <> s.hash THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
```
Em Python: `DeltaTable.forName(spark, "...").merge(source, cond).whenMatched...`.

### SCD Type 2 com MERGE (padrão)
1. Fechar a versão vigente que mudou: `UPDATE SET valid_to = now(), is_current = false`.
2. Inserir a nova versão: `INSERT (... valid_from = now(), valid_to = null, is_current = true)`.
Colunas de controle: `valid_from`, `valid_to`, `is_current`.

## Time Travel — auditoria e reprocessamento
```sql
SELECT * FROM gold.fato_voto VERSION AS OF 3;
SELECT * FROM gold.fato_voto TIMESTAMP AS OF '2026-06-01';
DESCRIBE HISTORY gold.fato_voto;     -- vê todas as versões
RESTORE TABLE gold.fato_voto TO VERSION AS OF 3;
```
Permite reconstruir o estado de qualquer data — atende "rastrear origem e
evolução dos dados" do desafio.

## Otimização
```sql
OPTIMIZE gold.fato_despesa ZORDER BY (id_deputado);  -- compacta + co-localiza
VACUUM gold.fato_despesa RETAIN 168 HOURS;           -- limpa arquivos órfãos
```
- `OPTIMIZE` resolve o problema de "muitos arquivos pequenos".
- `ZORDER` acelera filtros nas colunas indicadas.
- Tabelas managed fazem parte disso automaticamente (predictive optimization).

## Schema evolution
- `option("mergeSchema","true")` no append para aceitar colunas novas.
- `option("overwriteSchema","true")` no overwrite para trocar o schema.

## Carga incremental (estratégias)
- **Por ID/offset:** guarde o último ID processado, filtre `> ultimo_id`.
- **Por data:** filtre por `dataInicio/dataFim` desde o último run.
- **Por hash:** compare um hash do payload para detectar mudança (CDC).
- **Auto Loader** (`cloudFiles`): ingere só arquivos novos de um diretório.
