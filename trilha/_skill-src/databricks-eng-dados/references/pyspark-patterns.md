# PySpark — padrões para Engenharia de Dados

`spark` e `dbutils` já existem no notebook. Importe funções:
```python
from pyspark.sql import functions as F
from pyspark.sql.functions import col, to_timestamp, to_date, lit, current_timestamp
```

## Ler
```python
df = spark.read.json("/Volumes/workspace/bronze/raw/samples/deputados.jsonl")
df = spark.table("workspace.silver.deputados")
df = spark.read.format("delta").load("/Volumes/.../path")   # por caminho (evite)
```

## Renomear / selecionar / tipar (silver)
```python
df.selectExpr(
    "id as id_deputado",
    "siglaPartido as sigla_partido",
    "to_timestamp(dataHoraInicio) as data_hora_inicio",
    "deputado_.id as id_deputado",        # campo ANINHADO: acesso com ponto
).dropDuplicates(["id_deputado"])
```

## Dedup, join, agregação (gold)
```python
df.dropDuplicates(["id_frente", "id_deputado"])               # PK composta

atlas = (fm.join(dep, "id_deputado", "left")
           .join(fr, "id_frente", "left"))

resumo = (df.groupBy("sigla_partido")
            .agg(F.sum("valor_liquido").alias("total"),
                 F.countDistinct("id_votacao").alias("qtd")))
```

## Window functions (ranking, z-score, percentil)
```python
from pyspark.sql.window import Window

w = Window.partitionBy("tipo_despesa", "sigla_uf")
df = (df.withColumn("media", F.avg("valor_liquido").over(w))
        .withColumn("desvio", F.stddev("valor_liquido").over(w))
        .withColumn("zscore", (F.col("valor_liquido") - F.col("media")) / F.col("desvio"))
        .withColumn("anomalia", F.abs("zscore") > 3))

wr = Window.partitionBy("tipo_despesa").orderBy(F.desc("valor_liquido"))
df = df.withColumn("rank", F.row_number().over(wr))
```

## Escrever (delta managed)
```python
(df.write.format("delta").mode("overwrite")
   .option("overwriteSchema","true").saveAsTable("workspace.gold.fato_despesa"))
```

## Diferenças que pegam quem vem de pandas
- Spark é **lazy**: nada roda até uma ação (`count`, `show`, `write`, `collect`).
- Sem índice; ordenação só com `orderBy` (e é cara — evite sem necessidade).
- `display(df)` (notebook) vs `df.show(n, truncate=False)` (qualquer lugar).
- Strings de coluna com hífen/espaço: use crase no SQL ou `col("...")`.
- `F.col` para referência; evite Python puro linha-a-linha (use funções nativas
  Spark — performance e distribuição).
