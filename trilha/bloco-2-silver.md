# 🧪 Bloco 2 — Transformação / Prata (Silver)

> **Especialista do bloco:** Engenheiro de Transformação
> **Objetivo:** ler os JSONL crus da Bronze e produzir tabelas **limpas, tipadas e sem duplicatas** — padronizando nomes, convertendo datas, achatando estruturas aninhadas e deduplicando por chave primária. Sem regra de negócio ainda; isso é Gold.

---

## 1. Por que este bloco existe

A Bronze guardou o dado **como veio** — em `camelCase`, com datas como texto, objetos aninhados e possíveis duplicatas. Ninguém consegue analisar isso direito. A **Prata** é a camada que torna o dado **confiável e consistente**: nomes previsíveis, tipos corretos, uma linha por entidade. É a fronteira onde o dado deixa de ser "resposta de API" e vira "tabela".

A regra de ouro: a Prata **limpa e conforma, mas não inventa**. Nada de cálculo de negócio, ranking ou métrica — só deixar o dado correto e padronizado.

---

## 2. Conceitos em 3 níveis

### 2.1 Schema e padronização de nomes (snake_case)
- 🟢 **Júnior:** renomeio `siglaPartido` → `sigla_partido`, `idLegislatura` → `id_legislatura`. Tudo em `snake_case`.
- 🟡 **Pleno:** nomes consistentes viram **contrato**: quem consome a Prata sabe que toda chave de deputado se chama `id_deputado`, em qualquer tabela. Isso torna os JOINs previsíveis.
- 🔴 **Sênior:** padronizar nome cedo evita "dívida de schema" — se cada tabela chamar a mesma coisa de um jeito, a Gold vira um quebra-cabeça. O mapa de renomes é parte do **schema canônico** do projeto.

### 2.2 Tipagem (parse de datas, números)
- 🟢 **Júnior:** a API manda data como texto (`"2026-06-09T18:42:08"`); eu converto para datetime de verdade.
- 🟡 **Pleno:** tipo errado quebra agregação e ordenação. Datas como texto não comparam direito; valor monetário como string não soma. Converto com tratamento de erro (`coerce` → vira nulo em vez de explodir).
- 🔴 **Sênior:** tipagem é **qualidade de dado**. Um `valor_liquido` que virou texto silenciosamente vai dar soma errada na CEAP. Por isso parse explícito e auditável, com timestamps em UTC para não misturar fuso.

### 2.3 Flatten de estruturas aninhadas
- 🟢 **Júnior:** em `votacao_votos`, cada registro tem um objeto `deputado_` dentro. Eu "puxo" os campos para fora: `deputado_.id` → `id_deputado`.
- 🟡 **Pleno:** tabela tem que ser **plana** (colunas simples) para virar Parquet/Delta e ser consultada em SQL. Objeto aninhado não vira coluna direto.
- 🔴 **Sênior:** decidir *o que* achatar e *o que* descartar do aninhado é design de schema. Trazer `id/nome/partido/uf` do deputado e dispensar o resto mantém a tabela enxuta sem perder a chave de junção.

### 2.4 Deduplicação por chave primária
- 🟢 **Júnior:** se o mesmo deputado aparecer duas vezes, mantenho um. A PK de `deputados` é `id_deputado`.
- 🟡 **Pleno:** dedup precisa da **chave certa**. Em `frente_membros` a PK é composta: `id_frente` + `id_deputado` (a mesma pessoa pode estar em várias frentes). Manter a última ocorrência é uma política consciente.
- 🔴 **Sênior:** duplicata silenciosa infla contagem e distorce métrica. Definir PK por entidade é o que garante **grão** correto — base para os fatos da Gold não contarem duas vezes.

### 2.5 Qualidade de dados (a borda da Prata)
- 🟢 **Júnior:** confiro se a tabela não veio vazia e se as colunas-chave existem.
- 🟡 **Pleno:** valido contagem, nulos em campos críticos, e que a PK é realmente única depois do dedup.
- 🔴 **Sênior:** no Databricks isso vira **expectativas declarativas** (DLT `EXPECT`) que barram ou quarentenam dado ruim antes da Gold. É o tema do Bloco 5, mas a mentalidade começa aqui.

---

## 3. Mão na massa — reconstruindo a Silver

> Arquivo: `src/silver.py`. Lê os JSONL de `data/samples/`, devolve DataFrames pandas limpos.
> O código completo está na conversa do bloco; aqui ficam as ideias-âncora.

A espinha dorsal são **três dicionários de configuração** (igual fizemos na Bronze: config como dado):
- `RENAMES` — mapa `camelCase → snake_case` por entidade.
- `DATE_COLS` — quais colunas converter para data/timestamp.
- `PKS` — a chave primária de cada entidade (para o dedup).

E o fluxo de `to_silver(name)` é sempre o mesmo pipeline:
1. **lê** o JSONL cru (`_read_jsonl`);
2. caso especial: **achata** o `deputado_` dos votos;
3. `pd.json_normalize` para aplainar o que sobrou;
4. **descarta** as colunas de auditoria (`_audit_*`);
5. aplica **`RENAMES`**;
6. converte **datas** (`DATE_COLS`);
7. **deduplica** pela **`PKS`**.

A beleza é a **uniformidade**: uma função só trata as 10 entidades, porque o que muda entre elas está nos dicionários, não na lógica.

---

## ✅ O que você aprendeu
- O papel da Prata: **limpar e conformar**, sem regra de negócio.
- Padronizar nomes (`snake_case`) como **schema canônico** e contrato de JOIN.
- **Tipar** datas/números com tratamento de erro (`coerce`) e por que tipo errado é bug silencioso.
- **Achatar** o objeto `deputado_` aninhado dos votos.
- **Deduplicar** pela chave primária certa (inclusive PKs compostas).
- Config como dado de novo: `RENAMES`, `DATE_COLS`, `PKS` dirigem uma lógica única.

## 🎯 O que você deveria dominar para seguir
- Explicar por que a Prata não calcula métrica.
- Dar a PK de cada entidade e por que algumas são compostas.
- Saber o que `pd.json_normalize` e `errors="coerce"` fazem.
- Descrever os 7 passos de `to_silver` de cabeça.

## 📝 Quiz certo/errado (gabarito comentado)
1. *"A camada Prata é o lugar certo para calcular o ranking de gastos por partido."*
   ❌ **Errado.** Ranking é regra de negócio → Gold. A Prata só limpa e conforma.
2. *"`errors='coerce'` faz o parse falhar e abortar quando encontra uma data inválida."*
   ❌ **Errado.** `coerce` transforma o valor inválido em **nulo** (NaT), sem quebrar o processo.
3. *"A PK de `frente_membros` é composta por `id_frente` + `id_deputado`."*
   ✅ **Certo.** A mesma pessoa pode estar em várias frentes; a unicidade é do par.
4. *"Objetos JSON aninhados podem ser gravados como coluna de uma tabela Delta sem achatar."*
   ❌ **Errado (na prática deste projeto).** Aplainamos para colunas simples para consulta SQL e modelagem; o `deputado_` é achatado.
5. *"Padronizar nomes na Prata facilita os JOINs na Gold."*
   ✅ **Certo.** Toda tabela chamando a chave de `id_deputado` torna as junções previsíveis.

## 🎤 Perguntas de entrevista (com resposta-modelo)

**🟢 Júnior — "Qual a diferença entre as camadas Bronze e Prata?"**
> A Bronze guarda o dado cru, exatamente como veio da fonte, só com campos de auditoria. A Prata pega esse cru e limpa: padroniza nomes para snake_case, converte datas e números para os tipos certos e remove duplicatas. A Prata deixa o dado consistente; ela ainda não calcula nada de negócio.

**🟡 Pleno — "Como você garante que não há duplicatas e qual o risco se houver?"**
> Defino a chave primária de cada entidade — às vezes composta, como `id_frente` + `id_deputado` — e deduplico por ela, mantendo uma política clara (ex.: última ocorrência). O risco de duplicata é inflar contagens e distorcer métricas: um deputado contado duas vezes vira gasto ou presença dobrados na Gold. Depois do dedup eu valido que a PK ficou de fato única.

**🔴 Sênior — "Um valor monetário chegou como texto e ninguém percebeu. Que impacto isso tem e como você previne?"**
> Impacto silencioso e perigoso: somas e médias ficam erradas ou viram concatenação/erro, e o problema só aparece lá na frente, num KPI. Previno tipando explicitamente na Prata, com `coerce` para isolar valores inválidos como nulo em vez de mascarar, e valido a qualidade (nulos inesperados, faixa de valores). No Databricks eu formalizaria isso como expectativa declarativa (DLT) que quarentena o registro ruim antes da Gold, com alerta. Tipagem não é detalhe técnico — é a primeira linha de defesa da confiabilidade.

---

### ➡️ Próximo: **Bloco 3 — Ouro / Gold** (Modelador / Analytics Engineer): montar o star schema (dimensões + fatos), discutir fato/dimensão e SCD Type 2.
