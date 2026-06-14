# Lakeflow Declarative Pipelines (ex-DLT) + Expectations

> Renomeado em 2025/26: **Lakeflow Spark Declarative Pipelines** = o antigo
> **Delta Live Tables (DLT)**. Sintaxe compatível. Disponível inclusive no Free Edition.

## O que é
Um framework **declarativo**: você descreve as tabelas (materialized views /
streaming tables) e o Databricks gerencia dependências, ordem de execução,
checkpoints, retries e qualidade. Substitui orquestração manual de notebooks.

## Expectations — qualidade declarativa
Regras de qualidade aplicadas a cada registro. Três políticas de violação:

| Operador | O que faz no registro inválido |
|---|---|
| `expect` (warn) | **mantém** o registro, só conta a métrica de falha |
| `expect_or_drop` | **descarta** o registro inválido |
| `expect_or_fail` | **falha** a atualização do pipeline |

### Python
```python
import dlt   # (módulo mantém o nome 'dlt' por compatibilidade)

@dlt.table(name="silver_despesas")
@dlt.expect("valor_positivo", "valor_liquido >= 0")
@dlt.expect_or_drop("tem_deputado", "id_deputado IS NOT NULL")
@dlt.expect_or_fail("ano_valido", "ano BETWEEN 2023 AND 2026")
def silver_despesas():
    return spark.readStream.table("workspace.bronze.deputado_despesas")
```

### SQL
```sql
CREATE OR REFRESH STREAMING TABLE silver_despesas (
  CONSTRAINT valor_positivo EXPECT (valor_liquido >= 0),
  CONSTRAINT tem_deputado   EXPECT (id_deputado IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT ano_valido     EXPECT (ano BETWEEN 2023 AND 2026) ON VIOLATION FAIL UPDATE
) AS SELECT * FROM STREAM workspace.bronze.deputado_despesas;
```

## Novidades 2026 (úteis)
- Expectations podem ser **armazenadas no Unity Catalog** (regras versionadas,
  auditáveis, reusadas entre pipelines).
- Pipelines contínuos com >7 dias reiniciam graciosamente.
- Modo de execução **enfileirada** (queued) em vez de falhar por conflito.

## Como isso atende o desafio
- "Controle de qualidade declarativo" → expectations.
- "Resiliência/replay" → o pipeline gerencia retries e checkpoints; reprocessa via
  full refresh ou Time Travel da tabela alvo.
- "Streaming de votações" (opcional) → STREAMING TABLE consumindo micro-batches.

## Jobs (orquestração) — Lakeflow Jobs
Para agendar (ex.: coletar a cada 10 min) use **Lakeflow Jobs** (ex-Workflows):
tarefas encadeadas, triggers por tempo/arquivo, retries e alertas. Um Job pode
disparar o pipeline LDP e os notebooks.
