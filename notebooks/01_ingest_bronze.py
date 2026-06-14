# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Ingestão Bronze (Databricks + Delta + Unity Catalog)
# MAGIC
# MAGIC Lê os JSONL de `data/samples/` (coletados localmente, versionados no Git)
# MAGIC e materializa como tabelas **Delta** na camada **Bronze** do Unity Catalog.
# MAGIC
# MAGIC Pré-requisitos: este repo conectado como **Git folder** no Databricks.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuração — ajuste se o seu catálogo/caminho for diferente

# COMMAND ----------

import os

CATALOG = "workspace"   # no Databricks Free Edition o catálogo padrão é 'workspace'
VOL_SCHEMA = "bronze"   # schema onde fica o Volume de pouso dos arquivos crus
VOLUME = "raw"          # Volume UC para os JSONL

# O notebook está em notebooks/; o repositório é a pasta-pai.
# (Em Git folder do Databricks, os.getcwd() é a pasta do notebook.)
REPO_PATH = os.path.dirname(os.getcwd())
SAMPLES_SRC = f"{REPO_PATH}/data/samples"
VOL = f"/Volumes/{CATALOG}/{VOL_SCHEMA}/{VOLUME}"

print("REPO_PATH  :", REPO_PATH)
print("samples src:", SAMPLES_SRC)
print("Volume     :", VOL)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Criar schemas medalhão e o Volume no Unity Catalog

# COMMAND ----------

for schema in ("bronze", "silver", "gold"):
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{schema}")

spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{VOL_SCHEMA}.{VOLUME}")
dbutils.fs.mkdirs(f"{VOL}/samples")
print("schemas bronze/silver/gold e Volume prontos")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Copiar os JSONL do repo (Git folder) para o Volume
# MAGIC
# MAGIC A coleta roda **fora do cluster** (no seu PC). Aqui só "pousamos" o cru
# MAGIC no Volume — espelha a arquitetura: coleta separada do processamento.

# COMMAND ----------

import shutil

n = 0
for fname in os.listdir(SAMPLES_SRC):
    src = f"{SAMPLES_SRC}/{fname}"
    if fname.endswith(".jsonl") and os.path.getsize(src) > 0:
        shutil.copy(src, f"{VOL}/samples/{fname}")
        n += 1

print(f"{n} arquivos JSONL copiados para o Volume")
for f in dbutils.fs.ls(f"{VOL}/samples"):
    print(f"  {f.name}  {f.size} bytes")

# COMMAND ----------

# MAGIC %md
# MAGIC ## JSONL cru -> tabela Delta (Bronze) com campos de auditoria
# MAGIC
# MAGIC Uma tabela Delta por endpoint: `workspace.bronze.<endpoint>`.
# MAGIC `overwriteSchema=true` porque o schema inferido pode variar entre execuções.

# COMMAND ----------

from pyspark.sql.functions import lit, current_timestamp
from datetime import datetime, timezone

run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

bronze_counts = {}
for entry in dbutils.fs.ls(f"{VOL}/samples"):
    fname = entry.name
    if not fname.endswith(".jsonl"):
        continue
    name = fname[:-6]  # tira ".jsonl"
    try:
        df = (spark.read.json(f"{VOL}/samples/{fname}")
                   .withColumn("ingest_ts", current_timestamp())
                   .withColumn("run_id", lit(run_id))
                   .withColumn("endpoint", lit(name)))
        (df.write.format("delta")
           .mode("overwrite").option("overwriteSchema", "true")
           .saveAsTable(f"{CATALOG}.bronze.{name}"))
        bronze_counts[name] = df.count()
        print(f"  bronze.{name:<22s} {bronze_counts[name]:>6d} rows")
    except Exception as e:
        print(f"  bronze.{name}: FALHOU {str(e)[:120]}")

print(f"\nBronze: {sum(bronze_counts.values())} linhas em {len(bronze_counts)} tabelas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verificação

# COMMAND ----------

display(spark.table(f"{CATALOG}.bronze.deputados").limit(5))

# COMMAND ----------

# MAGIC %sql
# MAGIC -- a Bronze já é consultável em SQL
# MAGIC SELECT endpoint, count(*) AS linhas
# MAGIC FROM workspace.bronze.deputados
# MAGIC GROUP BY endpoint;
