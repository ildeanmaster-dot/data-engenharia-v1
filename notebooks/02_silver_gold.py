# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — Silver + Gold (PySpark + Delta)
# MAGIC
# MAGIC Lê as tabelas Delta da **Bronze** (`workspace.bronze.*`), aplica a limpeza
# MAGIC (Silver) e materializa o **star schema** + os **6 entregáveis** (Gold).
# MAGIC Tudo em tabelas managed do Unity Catalog.

# COMMAND ----------

CATALOG = "workspace"   # mesmo catálogo do notebook 01

from pyspark.sql import functions as F
from pyspark.sql.window import Window


def read_bronze(name):
    return spark.table(f"{CATALOG}.bronze.{name}")

def read_silver(name):
    return spark.table(f"{CATALOG}.silver.{name}")

def write_table(layer, name, df):
    (df.write.format("delta").mode("overwrite").option("overwriteSchema", "true")
       .saveAsTable(f"{CATALOG}.{layer}.{name}"))
    n = df.count()
    print(f"  {layer}.{name:<30s} {n:>6d} rows")
    return n

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver — rename para snake_case + tipagem + dedup
# MAGIC
# MAGIC Mesmas regras do `src/silver.py` local, mas em DataFrames Spark
# MAGIC (`selectExpr` para renomear, `dropDuplicates` para o dedup pela PK).

# COMMAND ----------

def silver_deputados():
    return read_bronze("deputados").selectExpr(
        "id as id_deputado", "nome", "siglaPartido as sigla_partido",
        "siglaUf as sigla_uf", "idLegislatura as id_legislatura", "email",
    ).dropDuplicates(["id_deputado"])

def silver_partidos():
    return read_bronze("partidos").selectExpr(
        "id as id_partido", "sigla as sigla_partido", "nome as nome_partido",
    ).dropDuplicates(["id_partido"])

def silver_frentes():
    return read_bronze("frentes").selectExpr(
        "id as id_frente", "titulo as nome_frente", "idLegislatura as id_legislatura",
    ).dropDuplicates(["id_frente"])

def silver_frente_membros():
    return read_bronze("frente_membros").selectExpr(
        "_parent_id as id_frente", "id as id_deputado", "nome as nome_deputado",
        "siglaPartido as sigla_partido", "siglaUf as sigla_uf",
    ).dropDuplicates(["id_frente", "id_deputado"])

def silver_orgaos():
    df = read_bronze("orgaos")
    selects = ["id as id_orgao", "sigla as sigla_orgao", "nome as nome_orgao",
               "tipoOrgao as tipo_orgao", "codTipoOrgao as cod_tipo_orgao"]
    if "dataInicio" in df.columns:
        selects.append("to_date(dataInicio) as data_inicio")
    if "dataFim" in df.columns:
        selects.append("to_date(dataFim) as data_fim")
    return df.selectExpr(*selects).dropDuplicates(["id_orgao"])

def silver_eventos():
    return read_bronze("eventos").selectExpr(
        "id as id_evento", "to_timestamp(dataHoraInicio) as data_hora_inicio",
        "to_timestamp(dataHoraFim) as data_hora_fim",
        "descricaoTipo as descricao_tipo", "situacao",
    ).dropDuplicates(["id_evento"])

def silver_evento_deputados():
    return read_bronze("evento_deputados").selectExpr(
        "_parent_id as id_evento", "id as id_deputado",
        "siglaPartido as sigla_partido", "siglaUf as sigla_uf",
    ).dropDuplicates(["id_evento", "id_deputado"])

def silver_votacoes():
    return read_bronze("votacoes").selectExpr(
        "id as id_votacao", "to_timestamp(dataHoraRegistro) as data_hora_registro",
        "descricao",
    ).dropDuplicates(["id_votacao"])

def silver_votacao_votos():
    # 'deputado_' é um struct aninhado -> acesso com ponto
    return read_bronze("votacao_votos").selectExpr(
        "_parent_id as id_votacao", "deputado_.id as id_deputado",
        "deputado_.nome as nome_deputado", "deputado_.siglaPartido as sigla_partido",
        "deputado_.siglaUf as sigla_uf", "tipoVoto as tipo_voto",
    ).dropDuplicates(["id_votacao", "id_deputado"])

def silver_deputado_despesas():
    return read_bronze("deputado_despesas").selectExpr(
        "_parent_id as id_deputado", "ano", "mes", "tipoDespesa as tipo_despesa",
        "codDocumento as cod_documento", "valorLiquido as valor_liquido",
        "nomeFornecedor as nome_fornecedor", "cnpjCpfFornecedor as cnpj_fornecedor",
        "to_timestamp(dataDocumento) as data_documento",
    ).dropDuplicates(["id_deputado", "cod_documento"])

SILVER = {
    "deputados": silver_deputados, "partidos": silver_partidos,
    "frentes": silver_frentes, "frente_membros": silver_frente_membros,
    "orgaos": silver_orgaos, "eventos": silver_eventos,
    "evento_deputados": silver_evento_deputados, "votacoes": silver_votacoes,
    "votacao_votos": silver_votacao_votos, "deputado_despesas": silver_deputado_despesas,
}

for name, fn in SILVER.items():
    try:
        write_table("silver", name, fn())
    except Exception as e:
        print(f"  silver.{name}: FALHOU {str(e)[:120]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold — dimensões e fatos (star schema)

# COMMAND ----------

dep  = read_silver("deputados")
part = read_silver("partidos")
fr   = read_silver("frentes")
fm   = read_silver("frente_membros")
orgs = read_silver("orgaos")
ev   = read_silver("eventos")
ed   = read_silver("evento_deputados")
vt   = read_silver("votacoes")
vv   = read_silver("votacao_votos")
desp = read_silver("deputado_despesas")

write_table("gold", "dim_deputado",
            dep.select("id_deputado", "nome", "sigla_partido", "sigla_uf", "id_legislatura"))
write_table("gold", "dim_partido", part)
write_table("gold", "dim_frente", fr)
write_table("gold", "dim_orgao",
            orgs.select("id_orgao", "sigla_orgao", "nome_orgao", "tipo_orgao", "cod_tipo_orgao"))
write_table("gold", "dim_evento",
            ev.select("id_evento", "data_hora_inicio", "data_hora_fim", "descricao_tipo", "situacao"))

write_table("gold", "fato_voto", vv.select("id_votacao", "id_deputado", "tipo_voto"))
write_table("gold", "fato_presenca", ed.select("id_evento", "id_deputado", "sigla_partido", "sigla_uf"))
write_table("gold", "fato_despesa", desp)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Entregável 1 — Atlas das frentes + HHI (Herfindahl)

# COMMAND ----------

atlas = (fm.join(dep, "id_deputado", "left").join(fr, "id_frente", "left")
           .select("id_frente", fr.nome_frente, "id_deputado",
                   dep.nome.alias("nome"), dep.sigla_partido, dep.sigla_uf))
write_table("gold", "gold_atlas_frentes", atlas)

part_frente = atlas.groupBy("id_frente", "sigla_partido").count().withColumnRenamed("count", "n_part")
tot_frente = atlas.groupBy("id_frente").count().withColumnRenamed("count", "total")
hhi = (part_frente.join(tot_frente, "id_frente")
       .withColumn("share", F.col("n_part") / F.col("total"))
       .groupBy("id_frente")
       .agg(F.sum(F.pow("share", 2)).alias("hhi"),
            F.first("total").alias("n_membros"),
            F.countDistinct("sigla_partido").alias("n_partidos"))
       .join(fr.select("id_frente", "nome_frente"), "id_frente", "left")
       .orderBy("hhi"))
write_table("gold", "gold_frente_diversidade", hhi)
display(hhi.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Entregável 2 — Calendário / presença

# COMMAND ----------

total_eventos = ev.select("id_evento").distinct().count()
taxa = (ed.groupBy("id_deputado").count().withColumnRenamed("count", "n_presencas")
          .join(dep, "id_deputado")
          .withColumn("total_eventos", F.lit(total_eventos))
          .withColumn("taxa_presenca", F.col("n_presencas") / F.col("total_eventos"))
          .select("id_deputado", "nome", "sigla_partido", "sigla_uf",
                  "n_presencas", "total_eventos", "taxa_presenca")
          .orderBy(F.desc("taxa_presenca")))
write_table("gold", "gold_taxa_presenca", taxa)

densidade = (ev.withColumn("ano", F.year("data_hora_inicio"))
               .withColumn("semana", F.weekofyear("data_hora_inicio"))
               .groupBy("ano", "semana").count().withColumnRenamed("count", "qtd_eventos")
               .orderBy("ano", "semana"))
write_table("gold", "gold_densidade_semanal", densidade)

write_table("gold", "gold_eventos_futuros",
            ev.filter(F.col("data_hora_inicio") > F.current_timestamp()))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Entregável 3 — Alinhamento frente × partido

# COMMAND ----------

votos_validos = vv.filter(F.col("tipo_voto").isin("Sim", "Nao"))

def _alinhamento(df, group_col):
    pivot = (df.groupBy("id_votacao", group_col, "tipo_voto").count()
               .groupBy("id_votacao", group_col).pivot("tipo_voto", ["Sim", "Nao"])
               .sum("count").na.fill(0))
    return (pivot.withColumn("total", F.col("Sim") + F.col("Nao"))
                 .filter(F.col("total") >= 2)
                 .withColumn("alinhamento",
                             F.greatest("Sim", "Nao") / F.col("total")))

resumo_partido = (_alinhamento(votos_validos, "sigla_partido")
                  .groupBy("sigla_partido")
                  .agg(F.avg("alinhamento").alias("alinhamento_medio"),
                       F.countDistinct("id_votacao").alias("qtd_votacoes"))
                  .orderBy(F.desc("alinhamento_medio")))
write_table("gold", "gold_alinhamento_partido", resumo_partido)

votos_frente = votos_validos.join(fm.select("id_frente", "id_deputado"), "id_deputado")
resumo_frente = (_alinhamento(votos_frente, "id_frente")
                 .groupBy("id_frente")
                 .agg(F.avg("alinhamento").alias("alinhamento_medio"),
                      F.countDistinct("id_votacao").alias("qtd_votacoes"))
                 .join(fr.select("id_frente", "nome_frente"), "id_frente", "left")
                 .orderBy(F.desc("alinhamento_medio")))
write_table("gold", "gold_alinhamento_frente", resumo_frente)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Entregável 4 — Raio-X CEAP (ranking, mensal e z-score de anomalia)

# COMMAND ----------

ranking_forn = (desp.groupBy("cnpj_fornecedor", "nome_fornecedor")
                    .agg(F.sum("valor_liquido").alias("valor_total"),
                         F.count("cod_documento").alias("qtd_documentos"),
                         F.countDistinct("id_deputado").alias("qtd_deputados"))
                    .orderBy(F.desc("valor_total")))
write_table("gold", "gold_ceap_ranking_fornecedor", ranking_forn.limit(100))

mensal = (desp.join(dep.select("id_deputado", "sigla_partido"), "id_deputado", "left")
              .groupBy("ano", "mes", "sigla_partido")
              .agg(F.sum("valor_liquido").alias("total"),
                   F.count("cod_documento").alias("qtd"))
              .orderBy("ano", "mes", F.desc("total")))
write_table("gold", "gold_ceap_mensal_partido", mensal)

# z-score de anomalia por (categoria × UF) — usando window
w_anom = Window.partitionBy("tipo_despesa", "sigla_uf")
anom = (desp.join(dep.select("id_deputado", "nome", "sigla_partido", "sigla_uf"), "id_deputado", "left")
            .withColumn("media_grupo", F.avg("valor_liquido").over(w_anom))
            .withColumn("desvio_grupo", F.stddev("valor_liquido").over(w_anom))
            .withColumn("zscore", (F.col("valor_liquido") - F.col("media_grupo")) / F.col("desvio_grupo"))
            .withColumn("anomalia", F.abs("zscore") > 3)
            .filter("anomalia")
            .select("id_deputado", "nome", "sigla_partido", "sigla_uf", "tipo_despesa",
                    "valor_liquido", "media_grupo", "desvio_grupo", "zscore",
                    "nome_fornecedor", "cnpj_fornecedor", "data_documento")
            .orderBy(F.desc("zscore")))
write_table("gold", "gold_ceap_anomalia_zscore", anom)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Entregável 5 — CPIs

# COMMAND ----------

cpis = orgs.filter(F.col("nome_orgao").rlike("(?i)CPI|CPMI|Inqu[eé]rito"))
if "data_inicio" not in cpis.columns:
    cpis = cpis.withColumn("data_inicio", F.lit(None).cast("date"))
if "data_fim" not in cpis.columns:
    cpis = cpis.withColumn("data_fim", F.lit(None).cast("date"))
cpis = (cpis.withColumn("duracao_dias", F.datediff("data_fim", "data_inicio"))
            .withColumn("excedeu_prazo", F.coalesce(F.col("duracao_dias") > 180, F.lit(False))))
write_table("gold", "gold_cpis", cpis)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Entregável 6 — Engajamento + absenteísmo

# COMMAND ----------

n_pres = ed.groupBy("id_deputado").count().withColumnRenamed("count", "n_presencas")
n_vot = vv.groupBy("id_deputado").count().withColumnRenamed("count", "n_votos")
eng = (dep.select("id_deputado", "nome", "sigla_partido", "sigla_uf")
          .join(n_pres, "id_deputado", "left").join(n_vot, "id_deputado", "left")
          .na.fill(0, ["n_presencas", "n_votos"]))

def _norm(df, c):
    row = df.agg((F.max(c) - F.min(c)).alias("rng"), F.min(c).alias("mn")).collect()[0]
    rng = row["rng"] or 1
    return df.withColumn(f"{c}_norm", (F.col(c) - F.lit(row["mn"] or 0)) / F.lit(rng))

eng = _norm(_norm(eng, "n_presencas"), "n_votos")
eng = (eng.withColumn("engajamento", (F.col("n_presencas_norm") + F.col("n_votos_norm")) / 2)
          .withColumn("percentil", F.percent_rank().over(Window.orderBy("engajamento"))))
write_table("gold", "gold_engajamento", eng.orderBy(F.desc("engajamento")))

total_v = vv.select("id_votacao").distinct().count()
votou = vv.groupBy("id_deputado").agg(F.countDistinct("id_votacao").alias("n_votou"))
absent = (dep.select("id_deputado", "nome", "sigla_partido", "sigla_uf")
             .join(votou, "id_deputado", "left").na.fill(0, ["n_votou"])
             .withColumn("n_ausencias", F.lit(total_v) - F.col("n_votou"))
             .withColumn("taxa_ausencia", F.col("n_ausencias") / F.lit(total_v))
             .orderBy(F.desc("taxa_ausencia")))
write_table("gold", "gold_absenteismo", absent)

# COMMAND ----------

print("=== Pipeline Silver + Gold concluído ===")
print(f"Tabelas em {CATALOG}.silver.* e {CATALOG}.gold.*")
