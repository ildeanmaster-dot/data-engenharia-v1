# 📚 Dicionário de Dados — API Câmara dos Deputados

> Referência das entidades coletadas, seu **grão** (chave primária), os **campos principais** (nome cru da API → nome padronizado na camada Prata) e **para que servem** nos entregáveis.
> Fonte: `https://dadosabertos.camara.leg.br/api/v2` · Atualizado na trilha (Bloco 1).

---

## Convenções

- **Grão / PK:** o que identifica uma linha única na entidade (usado para deduplicar na Prata).
- **Cru → Prata:** o campo vem da API com nome em `camelCase` e é renomeado para `snake_case` na Silver.
- **Campos de auditoria** (em *toda* entidade Bronze): `ingest_ts` (quando coletamos, UTC), `source_url` (URL exata da chamada), `endpoint` (nome lógico). Em fan-outs há também `_parent_id` (id do pai que originou o registro).

---

## 1. `deputados` — lista de parlamentares
**Tipo:** simples (paginado) · **Grão / PK:** `id_deputado`

| Cru (API) | Prata | Tipo | Descrição |
|---|---|---|---|
| `id` | `id_deputado` | int | Identificador único do deputado |
| `nome` | `nome` | texto | Nome parlamentar |
| `siglaPartido` | `sigla_partido` | texto | Partido atual (ex.: PT, PL) |
| `siglaUf` | `sigla_uf` | texto | Estado que representa (ex.: SP) |
| `idLegislatura` | `id_legislatura` | int | Legislatura (57 = atual) |
| `urlFoto` | `url_foto` | texto | Foto oficial |
| `email` | `email` | texto | E-mail funcional (confirmado na API) |
| `uriPartido` | `uri_partido` | texto | Link HATEOAS para o partido |

**Serve para:** dimensão central (`dim_deputado`); base de despesas, presença, votos e engajamento.

---

## 2. `partidos` — partidos políticos
**Tipo:** simples (paginado) · **Grão / PK:** `id_partido`

| Cru (API) | Prata | Tipo | Descrição |
|---|---|---|---|
| `id` | `id_partido` | int | Identificador do partido |
| `sigla` | `sigla_partido` | texto | Sigla (chave de junção com deputados) |
| `nome` | `nome_partido` | texto | Nome completo |

**Serve para:** dimensão `dim_partido`; agregações por partido (CEAP, alinhamento).

---

## 3. `frentes` — frentes parlamentares
**Tipo:** simples (paginado) · **Grão / PK:** `id_frente`

| Cru (API) | Prata | Tipo | Descrição |
|---|---|---|---|
| `id` | `id_frente` | int | Identificador da frente |
| `titulo` | `nome_frente` | texto | Nome/tema da frente |
| `idLegislatura` | `id_legislatura` | int | Legislatura da frente |

**Serve para:** **Atlas das frentes** (entregável 1); diversidade partidária (índice de Herfindahl).

---

## 4. `frente_membros` — composição das frentes (fan-out de `frentes`)
**Tipo:** fan-out · **Grão / PK:** `id_frente` + `id_deputado`

| Cru (API) | Prata | Tipo | Descrição |
|---|---|---|---|
| `_parent_id` | `id_frente` | int | Frente a que o membro pertence |
| `id` | `id_deputado` | int | Deputado membro |
| `nome` | `nome_deputado` | texto | Nome do membro |
| `siglaPartido` | `sigla_partido` | texto | Partido do membro |
| `siglaUf` | `sigla_uf` | texto | UF do membro |

**Serve para:** interseção frente × partido × UF; deputados em mais frentes; sobreposição entre frentes opostas.

---

## 5. `orgaos` — órgãos legislativos (comissões, CPIs, etc.)
**Tipo:** simples (paginado) · **Grão / PK:** `id_orgao`

| Cru (API) | Prata | Tipo | Descrição |
|---|---|---|---|
| `id` | `id_orgao` | int | Identificador do órgão |
| `sigla` | `sigla_orgao` | texto | Sigla do órgão |
| `nome` | `nome_orgao` | texto | Nome do órgão |
| `codTipoOrgao` | `cod_tipo_orgao` | int | Código do tipo |
| `tipoOrgao` | `tipo_orgao` | texto | Tipo (comissão, CPI...) |
| `dataInicio` | `data_inicio` | data | Início de funcionamento |
| `dataFim` | `data_fim` | data | Fim (nulo se ativo) |

**Serve para:** dimensão `dim_orgao`; **auditoria de CPIs** (entregável 5); contexto dos eventos.

---

## 6. `eventos` — sessões, audiências, seminários
**Tipo:** simples (paginado) · **Grão / PK:** `id_evento`

| Cru (API) | Prata | Tipo | Descrição |
|---|---|---|---|
| `id` | `id_evento` | int | Identificador do evento |
| `dataHoraInicio` | `data_hora_inicio` | timestamp | Início |
| `dataHoraFim` | `data_hora_fim` | timestamp | Fim |
| `descricaoTipo` | `descricao_tipo` | texto | Tipo do evento |

**Serve para:** **Calendário de eventos** (entregável 2); densidade semanal; eventos futuros.

---

## 7. `evento_deputados` — presença em eventos (fan-out de `eventos`)
**Tipo:** fan-out · **Grão / PK:** `id_evento` + `id_deputado`

| Cru (API) | Prata | Tipo | Descrição |
|---|---|---|---|
| `_parent_id` | `id_evento` | int | Evento |
| `id` | `id_deputado` | int | Deputado presente |
| `siglaPartido` | `sigla_partido` | texto | Partido |
| `siglaUf` | `sigla_uf` | texto | UF |

**Serve para:** `fato_presenca`; taxa de presença por deputado/tipo; engajamento.

---

## 8. `votacoes` — votações nominais
**Tipo:** simples (paginado) · **Grão / PK:** `id_votacao`

| Cru (API) | Prata | Tipo | Descrição |
|---|---|---|---|
| `id` | `id_votacao` | texto | Identificador da votação |
| `dataHoraRegistro` | `data_hora_registro` | timestamp | Quando foi registrada |

**Serve para:** **correlação frentes × votações** (entregável 3); absenteísmo; engajamento.

---

## 9. `votacao_votos` — votos individuais (fan-out de `votacoes`)
**Tipo:** fan-out · **Grão / PK:** `id_votacao` + `id_deputado`
> ⚠️ Particularidade 1: o registro traz um objeto **`deputado_` aninhado** que é achatado na Prata.
> ⚠️ Particularidade 2: **votos individuais só existem em votação NOMINAL** (registrada voto a voto, sobretudo no **Plenário**, órgão `idOrgao=180`). A maioria das votações é **simbólica** e retorna `/votos` vazio. Por isso coletamos votações do Plenário e filtramos só as que têm placar na descrição (`"...Total: N"`) antes do fan-out.

| Cru (API) | Prata | Tipo | Descrição |
|---|---|---|---|
| `_parent_id` | `id_votacao` | texto | Votação |
| `tipoVoto` | `tipo_voto` | texto | Sim / Não / Abstenção / Obstrução |
| `dataRegistroVoto` | `data_registro_voto` | timestamp | Quando o voto foi dado |
| `deputado_.id` | `id_deputado` | int | Deputado (do objeto aninhado) |
| `deputado_.nome` | `nome_deputado` | texto | Nome |
| `deputado_.siglaPartido` | `sigla_partido` | texto | Partido |
| `deputado_.siglaUf` | `sigla_uf` | texto | UF |

**Serve para:** `fato_voto`; alinhamento de voto por frente vs. partido; votações perdidas.

---

## 10. `deputado_despesas` — cota parlamentar / CEAP (fan-out de `deputados`)
**Tipo:** fan-out, por ano (`ANOS_CEAP`) · **Grão / PK:** `id_deputado` + `cod_documento`

| Cru (API) | Prata | Tipo | Descrição |
|---|---|---|---|
| `_parent_id` | `id_deputado` | int | Deputado que gastou |
| `ano` | `ano` | int | Ano da despesa (vem **pronto** — não precisa derivar da data) |
| `mes` | `mes` | int | Mês da despesa (1–12, **pronto** — facilita agregação mensal) |
| `tipoDespesa` | `tipo_despesa` | texto | Categoria (combustível, divulgação...) |
| `codDocumento` | `cod_documento` | int | Id da nota/documento (parte da PK) |
| `tipoDocumento` | `tipo_documento` | texto | Nota fiscal, recibo, etc. |
| `numDocumento` | `num_documento` | texto | Número do documento fiscal |
| `valorDocumento` | `valor_documento` | decimal | Valor bruto do documento |
| `valorLiquido` | `valor_liquido` | decimal | Valor efetivamente reembolsado |
| `valorGlosa` | `valor_glosa` | decimal | Valor glosado (não reembolsado) |
| `dataDocumento` | `data_documento` | timestamp | Data da despesa |
| `nomeFornecedor` | `nome_fornecedor` | texto | Fornecedor |
| `cnpjCpfFornecedor` | `cnpj_fornecedor` | texto | CNPJ/CPF do fornecedor |
| `urlDocumento` | `url_documento` | texto | Link para a imagem da nota |

**Serve para:** **Raio-X CEAP** (entregável 4); `fato_despesa`; z-score de anomalia por categoria; ranking de fornecedores.

---

## Relacionamentos (visão rápida)

```
dim_partido ──< deputados >── frente_membros >── frentes
                   │  │  │
                   │  │  └──< deputado_despesas (por ano)
                   │  └─────< evento_deputados >── eventos >── orgaos
                   └────────< votacao_votos >── votacoes
```

- `deputados.sigla_partido` → `partidos.sigla_partido`
- `frente_membros` liga `frentes` ↔ `deputados` (N:N)
- `evento_deputados` liga `eventos` ↔ `deputados` (presença)
- `votacao_votos` liga `votacoes` ↔ `deputados` (voto)
- `deputado_despesas` pendura em `deputados` (1:N), particionável por ano
- `eventos.id_orgao` → `orgaos.id_orgao` (qual comissão/CPI promoveu)
