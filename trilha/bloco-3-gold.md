# 🧱 Bloco 3 — Ouro / Gold (star schema + entregáveis)

> **Especialista do bloco:** Modelador / Analytics Engineer
> **Objetivo:** montar o **star schema** (dimensões + fatos) a partir da Prata e produzir os **6 entregáveis analíticos** do desafio. Discutir fato/dimensão, grão e **SCD Type 2**.

---

## 1. Por que este bloco existe

A Prata deixou o dado limpo, mas ainda "cru de negócio". A **Gold** é onde o dado vira **resposta**: métricas, rankings, scores de anomalia. O desafio cobra explicitamente "modelagem e otimização de tabelas" e "comparar e justificar modelos (fato/dimensão, SCD2)". É o bloco que separa quem move dado de quem **modela** dado.

---

## 2. Star schema em 3 níveis

- 🟢 **Júnior:** tabelas de **fato** no centro (eventos medidos: voto, despesa, presença) cercadas por **dimensões** (descrições: deputado, partido, frente, órgão, evento). Lembra uma estrela.
- 🟡 **Pleno:** a dimensão responde "por quais ângulos eu analiso?"; o fato responde "o que eu meço?". O fato guarda só **IDs + medidas** (não o nome do deputado) — isso o mantém enxuto e os JOINs baratos.
- 🔴 **Sênior:** star schema é modelo **OLAP** (leitura analítica), diferente do **OLTP** normalizado de um banco transacional. Troca-se redundância controlada por performance e simplicidade. É o modelo recomendado pela arquitetura medalhão na camada Ouro.

### Dimensão × Fato × Grão
- **Dimensão** (`dim_*`): uma linha por entidade única, descritiva e estável.
- **Fato** (`fato_*`): uma linha por evento medido; cresce muito.
- **Grão:** a definição de "o que é uma linha" no fato. Errar o grão (misturar despesa-por-nota com despesa-por-mês) **dobra contagem**. O dedup da Prata é o que protege o grão.

| Fato | Grão | Medida |
|---|---|---|
| `fato_voto` | votação × deputado | tipo_voto |
| `fato_presenca` | evento × deputado | (contagem) |
| `fato_despesa` | deputado × documento | valor_liquido |

---

## 3. Os 6 entregáveis (conceitos analíticos)

1. **Atlas das frentes — índice de Herfindahl (HHI).** HHI = soma dos quadrados das participações de cada partido na frente. Baixo = diverso; alto = concentrado. Vem da economia (concentração de mercado). *Ressalva:* partido pequeno atinge alinhamento/coesão alto trivialmente — pondere por tamanho do grupo.
2. **Calendário de eventos.** Taxa de presença (presenças ÷ total de eventos), densidade por semana ISO, view de eventos futuros.
3. **Correlação frente × votação.** Para cada votação+grupo, % do voto majoritário (só Sim/Não). Compara coesão dentro de frentes vs. dentro de partidos.
4. **Raio-X CEAP + anomalia.** Ranking de fornecedores, gasto mensal por partido, e **z-score por (categoria × UF)**: `z = (valor − média_grupo) / desvio_grupo`; `|z| > 3` = atípico. *Ressalva:* grupos pequenos têm desvio instável; exija amostra mínima e combine com regras.
5. **Auditoria de CPIs.** Filtra órgãos cujo nome contém CPI/CPMI/Inquérito; calcula duração e se excedeu 180 dias. *Limitação:* a API expõe sobretudo órgãos ativos.
6. **Engajamento e absenteísmo.** Score min-max de presenças + votos (com percentil) e taxa de ausência em votações.

---

## 4. SCD Type 2 — Slowly Changing Dimension

**Problema:** uma dimensão muda no tempo. Um deputado **troca de partido**. Se `dim_deputado` só guarda o partido atual, um voto de 2023 aparece com o partido errado.

| Tipo | O que faz | Quando usar |
|---|---|---|
| **Type 1** | sobrescreve (perde história) | quando o passado não importa |
| **Type 2** | versiona: nova linha por mudança | quando o histórico importa |
| **Type 3** | guarda só o valor anterior | uma única troca |

**Type 2 na prática** — colunas de validade:

| id_deputado | sigla_partido | valid_from | valid_to | is_current |
|---|---|---|---|---|
| 204379 | PSDB | 2023-02-01 | 2024-05-09 | false |
| 204379 | MDB | 2024-05-10 | (null) | true |

- 🟢 **Júnior:** Type 2 guarda histórico criando uma linha nova por mudança.
- 🟡 **Pleno:** para "qual era o partido na data do voto", faz-se um **join temporal** (`data` entre `valid_from` e `valid_to`).
- 🔴 **Sênior:** no Delta implementa-se com **`MERGE`** (fecha a linha antiga, insere a nova) e reconstrói-se o passado com **Time Travel**. É a base do desafio opcional de **CDC de tramitação** (Bloco 6).

**Decisão deste projeto:** as dimensões são uma "foto" da legislatura atual → **Type 1 basta** para os 6 entregáveis. Type 2 entra no CDC de proposições. Decisão consciente, registrada.

---

## 5. Como o código se organiza (`src/gold.py`)
Mesma filosofia das camadas anteriores: funções pequenas e um orquestrador.
- `build_dims(silver)` → 5 dimensões (projeções via helper `_select`, que ignora coluna ausente).
- `build_facts(silver)` → 3 fatos (só IDs + medidas).
- funções `gold_*` → um entregável cada.
- `build_all(silver)` → monta tudo (22 tabelas). O `runner.py` chama e materializa em Parquet (`data/gold/`), equivalente local ao Delta.

---

## ✅ O que você aprendeu
- Montar um **star schema**: dimensões descritivas + fatos medidos.
- O conceito de **grão** e por que ele protege contra dupla contagem.
- Calcular **HHI**, taxa de presença, **alinhamento** de voto, **z-score** de anomalia, e scores de engajamento.
- **SCD Type 1 vs 2 vs 3** e quando cada um se aplica.
- Materializar a Gold em Parquet (Delta no Databricks).

## 🎯 O que você deveria dominar para seguir
- Explicar dimensão vs fato e dar o grão de cada fato do projeto.
- Defender por que usamos Type 1 aqui e onde Type 2 seria necessário.
- Descrever como o z-score detecta anomalia e suas limitações.
- Saber por que o fato guarda ID e não o nome.

## 📝 Quiz certo/errado (gabarito comentado)
1. *"A tabela de fato deve guardar o nome do deputado para facilitar relatórios."*
   ❌ **Errado.** O fato guarda o `id_deputado`; o nome fica na dimensão. Isso mantém o fato enxuto e evita redundância.
2. *"HHI alto significa frente partidariamente diversa."*
   ❌ **Errado.** HHI **alto** = concentrado (um partido domina). Diverso = HHI **baixo**.
3. *"SCD Type 2 cria uma nova linha a cada mudança, preservando o histórico."*
   ✅ **Certo.** Com `valid_from`/`valid_to`/`is_current`.
4. *"Um z-score de 16 sempre indica fraude comprovada."*
   ❌ **Errado.** Indica desvio estatístico atípico — ponto de partida da investigação, não veredito. Grupos pequenos inflam o z.
5. *"Definir o grão errado do fato pode causar dupla contagem nas métricas."*
   ✅ **Certo.** Misturar grãos (nota vs mês) duplica somas.

## 🎤 Perguntas de entrevista (com resposta-modelo)

**🟢 Júnior — "O que é um star schema?"**
> É um modelo dimensional com tabelas de fato no centro — que guardam os eventos medidos, como votos e despesas, só com IDs e valores — cercadas por tabelas de dimensão, que guardam as descrições, como nome do deputado e do partido. Junto fato e dimensão por ID quando preciso analisar. É otimizado para consultas analíticas.

**🟡 Pleno — "Quando você usaria SCD Type 2 em vez de Type 1?"**
> Type 1 sobrescreve e perde o histórico; serve quando só o estado atual importa. Type 2 cria uma versão nova a cada mudança, com janelas de validade, e serve quando preciso reconstruir o passado — por exemplo, saber a que partido um deputado pertencia na data de um voto. Neste projeto as dimensões são uma foto da legislatura, então Type 1 basta; mas para rastrear a tramitação de uma proposição, onde cada mudança de status importa, eu usaria Type 2 com MERGE no Delta e Time Travel.

**🔴 Sênior — "Como você projetou a detecção de anomalia na CEAP e quais são suas limitações?"**
> Usei z-score agrupando por categoria de despesa e UF do deputado, comparando cada gasto com a média e o desvio dos pares do mesmo contexto; marco como anômalo o que passa de três desvios. É interpretável e barato. As limitações: em grupos pequenos o desvio é instável e infla o z, gerando falso positivo; o z-score assume distribuição aproximadamente normal, o que gastos com cauda longa violam; e anomalia estatística não é prova de irregularidade. Por isso eu exigiria amostra mínima por grupo, combinaria com regras de negócio (tetos por categoria) e trataria o score como gatilho de auditoria, não como veredito. Documentaria essa decisão no registro técnico.

---

### ➡️ Próximo: levar este pipeline para o **Databricks/PySpark** (notebooks medalhão), depois **qualidade/DLT/runbook** (Bloco 5) e **carga incremental/CDC** (Bloco 6).
