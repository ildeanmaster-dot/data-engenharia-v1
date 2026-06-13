# 🎓 Trilha Didática — Fast Track Engenharia de Dados (V11)

> **Projeto base:** Pipeline ponta-a-ponta sobre os Dados Abertos da Câmara dos Deputados, no Databricks, com arquitetura medalhão (Bronze → Prata/Silver → Ouro/Gold).
> **Modo de aprendizado:** reconstruir do zero, com o código existente servindo de *gabarito*.
> **Ambiente:** Databricks real (Free Edition ou corporativo) + ambiente local para iterar rápido.
> **Profundidade:** cada conceito é apresentado em três níveis — 🟢 Júnior, 🟡 Pleno, 🔴 Sênior.

---

## 1. Por que esta trilha existe

O desafio final do Fast Track não é "rodar um script". Ele avalia se você sabe **construir uma solução de dados ponta a ponta** e — mais importante — **justificar cada decisão**. O enunciado pede explicitamente: desenhar a arquitetura, comparar modelos de tabela (SCD2, fato/dimensão), rastrear linhagem (auditoria, time travel), detectar anomalias, escrever runbooks, implementar carga incremental e resiliência.

Por isso a trilha não te entrega o código pronto. Ela te faz **reconstruir** cada peça entendendo o *porquê*. No fim de cada bloco você terá:

- o que você **aprendeu** na prática;
- o que você **deveria** dominar antes de seguir;
- um **quiz certo/errado** para fixar;
- **perguntas de entrevista** (com resposta-modelo) no nível júnior/pleno/sênior.

---

## 2. O "time" que vai te acompanhar

Em vez de um único tutor, você terá uma **equipe de especialistas** (personas). A cada bloco eu assumo o papel do especialista certo e explico do ponto de vista dele. Isso espelha como um time de dados real funciona.

| Especialista | Papel | Atua principalmente em |
|---|---|---|
| 🏛️ **Arquiteto de Dados** | Desenha a solução, define camadas e justifica trade-offs | Bloco 0, 7 |
| 🔌 **Engenheiro de Ingestão** | Coleta de APIs, paginação, retry, auditoria, idempotência | Bloco 1 (Bronze) |
| 🧪 **Engenheiro de Transformação** | Limpeza, tipagem, dedup, qualidade de dados | Bloco 2 (Silver) |
| 🧱 **Modelador / Analytics Engineer** | Star schema, fato/dimensão, SCD Type 2 | Bloco 3 (Gold) |
| 📊 **Analista de Dados** | Os 6 entregáveis analíticos, métricas, anomalias | Bloco 4 |
| 🛡️ **SRE / Confiabilidade** | DLT, expectativas, runbooks, replay, time travel | Bloco 5, 6 |
| 📝 **Redator Técnico** | Documentação, ADRs, README, defesa da entrega | Bloco 7 (transversal) |
| 🎤 **Mentor de Carreira** | Quizzes e simulação de entrevista ao fim de cada bloco | Todos os blocos |

> Por baixo dos panos, esses papéis acionam ferramentas reais quando útil: geração de código Python/PySpark, SQL, diagramas de arquitetura e documentos. Você não precisa se preocupar com isso — só seguir a aula.

---

## 3. O método dos 3 níveis

Todo conceito importante aparece em camadas, para você não só *fazer* mas *entender e defender*:

- 🟢 **Júnior — "o quê e como".** A definição, a sintaxe, o passo a passo para funcionar.
- 🟡 **Pleno — "as boas práticas".** Por que se faz assim, o que evita bug/dívida técnica, padrões do mercado.
- 🔴 **Sênior — "trade-offs e escala".** O que muda em produção, custo, falha, alternativas e como você defenderia a escolha numa revisão de arquitetura.

Exemplo rápido com *paginação de API*:
- 🟢 "A API devolve 100 itens por página; eu incremento `?pagina=`."
- 🟡 "Eu sigo o header `Link rel=next` em vez de chutar o número da página, porque é o contrato oficial e não quebra se a paginação mudar."
- 🔴 "Em volume real eu separo a ingestão do processamento, gravo o cru com `ingest_ts`/`source_url` para reprocessar, e trato 429 com backoff para não derrubar a fonte."

---

## 4. Mapa dos blocos

Cada bloco vira uma **apostila** (`trilha/NN_nome.md`). A ordem segue a construção natural do pipeline e cobre 100% do que o desafio cobra.

### Bloco 0 — Setup & Fundamentos 🏛️
Entender o desafio, os Dados Abertos, e montar o ambiente (Databricks + Git + local).
**Conceitos:** Engenharia de Dados, Lakehouse, Delta Lake, Unity Catalog, Volumes, arquitetura medalhão (o *desenho* da solução).
**Cobre do desafio:** "Arquitetura de Dados" (desenho completo + justificativa).

### Bloco 1 — Ingestão / Bronze 🔌
Construir o cliente da API e a camada bruta.
**Conceitos:** REST/JSON, paginação (`Link` header), retry com backoff, rate limiting, *fan-out* (endpoints filhos), campos de auditoria, JSONL cru → Delta.
**Cobre do desafio:** ingestão, controle de qualidade na borda, rastreio de origem.

### Bloco 2 — Transformação / Silver (Prata) 🧪
Limpar e padronizar os dados.
**Conceitos:** schema, snake_case, tipagem/parse de datas, *flatten* de estruturas aninhadas, deduplicação por chave primária, expectativas de qualidade.
**Cobre do desafio:** modelagem da prata, qualidade, relacionamentos entre tabelas.

### Bloco 3 — Modelagem / Gold (Ouro) 🧱
Montar o star schema.
**Conceitos:** dimensão vs fato, grão, chaves, **SCD Type 2** (valid_from/valid_to/is_current), por que/quando usar cada modelo.
**Cobre do desafio:** "Modelagem e Otimização de Tabelas" (comparar e justificar modelos).

### Bloco 4 — Entregáveis analíticos 📊
Os 6 produtos de dados, um sub-bloco cada:
1. **Atlas das frentes** — índice de Herfindahl (diversidade partidária).
2. **Calendário de eventos** — taxa de presença, densidade semanal, eventos futuros.
3. **Correlação frentes × votações** — alinhamento de voto.
4. **Raio-X CEAP** — z-score de anomalia por categoria, ranking de fornecedores.
5. **Auditoria de CPIs** — timeline, duração, produtividade.
6. **Score de engajamento** — presença × votações, percentis, série temporal.
**Cobre do desafio:** os 6 entregáveis + "Detecção de Padrões e Anomalias".

### Bloco 5 — Qualidade, Resiliência & Runbook 🛡️
Tornar o pipeline confiável.
**Conceitos:** testes (pytest), Delta Live Tables (DLT) com expectativas, runbook de incidentes, estratégia de replay/reprocessamento, **Delta Time Travel**.
**Cobre do desafio:** "Resiliência e Recuperação", "Documentação Técnica e Runbook".

### Bloco 6 — Carga Incremental & CDC (Sênior / opcionais) 🔴
Os desafios opcionais e o que separa pleno de sênior.
**Conceitos:** carga incremental (hash, controle por ID/offset), **CDC com SCD Type 2**, reconstrução por Time Travel, streaming/micro-batch com DLT, alertas.
**Cobre do desafio:** "Carga Incremental" + os 2 desafios opcionais.

### Bloco 7 — Documentação, Arquitetura final & Defesa 📝
Fechar o pacote de entrega.
**Conceitos:** diagrama de arquitetura final, ADRs (registro de decisões), README de produção, "defesa" da solução como numa banca/entrevista técnica.
**Cobre do desafio:** entregável final + boas práticas de manutenção/escalabilidade.

---

## 5. Estrutura de pastas da trilha

```
trilha/
├── 00_ROADMAP_TRILHA.md      <- este arquivo (o mapa)
├── 01_bronze.md              <- gerado ao concluirmos o Bloco 1
├── 02_silver.md
├── ...
└── _GABARITO/                <- onde guardamos referências ao código pronto
```

O código original do projeto (em `src/`, `notebooks/`) fica como **gabarito**: você tenta reconstruir, e a gente compara com a versão pronta para discutir as diferenças.

---

## 6. Como vamos trabalhar (o ritual de cada bloco)

1. **Abertura** — o especialista do bloco explica o objetivo e o *porquê* dele existir.
2. **Conceito em 3 níveis** — 🟢 → 🟡 → 🔴 para cada ideia-chave.
3. **Mão na massa** — eu te passo o passo a passo; **você executa em paralelo** e me mostra o resultado/erro.
4. **Comparação com o gabarito** — vemos como o projeto pronto resolveu e por quê.
5. **Fechamento da apostila** — gero o `.md` do bloco com:
   - ✅ O que você aprendeu
   - 🎯 O que você deveria dominar para seguir
   - 📝 Quiz certo/errado (com gabarito comentado)
   - 🎤 Perguntas de entrevista (júnior, pleno e sênior, com resposta-modelo)

---

## 7. Próximo passo

Começar pelo **Bloco 0 — Setup & Fundamentos**: entender o desafio em profundidade, decidir Databricks Free Edition vs. corporativo, e desenhar a arquitetura medalhão antes de escrever a primeira linha de ingestão.
