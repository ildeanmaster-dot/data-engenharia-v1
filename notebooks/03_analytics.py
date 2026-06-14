# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — Analytics: os 6 entregáveis em SQL
# MAGIC
# MAGIC Consome as tabelas Delta `workspace.gold.*` geradas no notebook 02.
# MAGIC Cada query representa um dos entregáveis do desafio.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Atlas das frentes: top 10 mais diversas (menor HHI)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT id_frente, nome_frente, n_membros, n_partidos, round(hhi, 4) AS hhi
# MAGIC FROM workspace.gold.gold_frente_diversidade
# MAGIC ORDER BY hhi ASC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Calendário: top 10 deputados por taxa de presença

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT nome, sigla_partido, sigla_uf, n_presencas,
# MAGIC        round(taxa_presenca, 3) AS taxa_presenca
# MAGIC FROM workspace.gold.gold_taxa_presenca
# MAGIC ORDER BY taxa_presenca DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 — Frentes mais coesas no voto (alinhamento médio)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT nome_frente, round(alinhamento_medio, 3) AS alinhamento, qtd_votacoes
# MAGIC FROM workspace.gold.gold_alinhamento_frente
# MAGIC WHERE qtd_votacoes >= 5
# MAGIC ORDER BY alinhamento DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 — Raio-X CEAP: top fornecedores e anomalias

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT nome_fornecedor, cnpj_fornecedor,
# MAGIC        round(valor_total, 2) AS valor_total, qtd_documentos, qtd_deputados
# MAGIC FROM workspace.gold.gold_ceap_ranking_fornecedor
# MAGIC ORDER BY valor_total DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- despesas anômalas (z-score > 3 frente aos pares de mesma categoria e UF)
# MAGIC SELECT nome, sigla_uf, tipo_despesa, round(valor_liquido, 2) AS valor,
# MAGIC        round(zscore, 1) AS zscore
# MAGIC FROM workspace.gold.gold_ceap_anomalia_zscore
# MAGIC ORDER BY zscore DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 — CPIs identificadas

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT sigla_orgao, nome_orgao, tipo_orgao,
# MAGIC        data_inicio, data_fim, duracao_dias, excedeu_prazo
# MAGIC FROM workspace.gold.gold_cpis
# MAGIC ORDER BY data_inicio DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 — Engajamento: top 10 mais engajados

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT nome, sigla_partido, sigla_uf, n_presencas, n_votos,
# MAGIC        round(engajamento, 3) AS engajamento, round(percentil, 3) AS percentil
# MAGIC FROM workspace.gold.gold_engajamento
# MAGIC ORDER BY engajamento DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6b — Absenteísmo: quem mais faltou em votações

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT nome, sigla_partido, sigla_uf, n_ausencias,
# MAGIC        round(taxa_ausencia, 3) AS taxa_ausencia
# MAGIC FROM workspace.gold.gold_absenteismo
# MAGIC WHERE taxa_ausencia > 0
# MAGIC ORDER BY taxa_ausencia DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bônus — verificação do star schema (contagens)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'dim_deputado' AS tabela, count(*) AS linhas FROM workspace.gold.dim_deputado
# MAGIC UNION ALL SELECT 'fato_voto',    count(*) FROM workspace.gold.fato_voto
# MAGIC UNION ALL SELECT 'fato_despesa', count(*) FROM workspace.gold.fato_despesa
# MAGIC UNION ALL SELECT 'fato_presenca',count(*) FROM workspace.gold.fato_presenca
# MAGIC ORDER BY linhas DESC;
