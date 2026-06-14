---
name: camara-dados-abertos
description: >
  Especialista na API de Dados Abertos da Câmara dos Deputados (v2). Use esta skill
  SEMPRE que o usuário trabalhar com dados da Câmara: endpoints de deputados, partidos,
  blocos, frentes, eventos, órgãos, comissões, CPIs, legislaturas, proposições (PL/PEC/MPV),
  votações, votos, despesas da cota parlamentar (CEAP), discursos ou tabelas de referência.
  Também use ao montar ingestão/ETL, paginação, fan-out, filtros por data/UF/partido/tipo,
  ou ao mapear campos da API para um pipeline (Bronze/Silver/Gold). Base:
  https://dadosabertos.camara.leg.br/api/v2
---

# API de Dados Abertos da Câmara dos Deputados (v2)

Guia operacional para consultar e ingerir dados legislativos da Câmara. Use-o para
escolher o endpoint certo, montar a URL com os parâmetros corretos, paginar com
segurança e entender o formato das respostas.

## Fatos essenciais (decore)

- **Base URL:** `https://dadosabertos.camara.leg.br/api/v2`
- **Sem autenticação** — API pública, só `GET`.
- **Formato padrão:** JSON. Também aceita XML/CSV via `?formato=xml` ou header `Accept`.
- **Envelope de toda lista:**
  ```json
  { "dados": [ ... ], "links": [ {"rel":"self|first|last|next|prev","href":"..."} ] }
  ```
  A lista está SEMPRE na chave `dados`. A paginação está em `links` (siga `rel="next"`).
- **Paginação:** `?pagina=N&itens=M`. `itens` máximo = **100** (default 15). Pare quando
  não houver `rel="next"` nos `links` (ou no header `Link`).
- **Ordenação:** `?ordem=ASC|DESC&ordenarPor=<campo>` (ex.: `ordenarPor=nome`).
- **Datas:** filtros `dataInicio`/`dataFim` no formato `AAAA-MM-DD`; timestamps vêm como
  `AAAA-MM-DDTHH:MM`.
- **Legislatura atual:** **57** (eleita em out/2022, mandato fev/2023–jan/2027). Use
  `idLegislatura=57` para recortar o período corrente.
- **HATEOAS:** quase todo objeto traz `uri` apontando para o próprio recurso e `uri<Algo>`
  (ex.: `uriPartido`) para recursos relacionados.

## Regras de robustez na ingestão

1. **Retry só em transitórios:** repita em `429, 500, 502, 503, 504` com **backoff
   exponencial**; em `4xx` (ex.: 404) não repita.
2. **Rate limit:** dê um `sleep` curto (~0.25s) entre páginas para não tomar 429.
3. **`itens=100`** sempre que possível: menos requisições para o mesmo volume.
4. **Fan-out controlado:** endpoints `/{id}/...` exigem coletar o pai antes; isso
   multiplica chamadas — limite quantos pais processa por execução.
5. **Auditoria:** ao gravar a camada bruta, carimbe `ingest_ts` (UTC) e `source_url`.

## Os 10 grupos de endpoints

| Grupo | Lista | Detalhe | Sub-recursos principais |
|---|---|---|---|
| **deputados** | `/deputados` | `/deputados/{id}` | `despesas`, `discursos`, `eventos`, `frentes`, `historico`, `ocupacoes`, `orgaos`, `profissoes`, `mandatosExternos` |
| **partidos** | `/partidos` | `/partidos/{id}` | `membros`, `lideres` |
| **blocos** | `/blocos` | `/blocos/{id}` | — |
| **frentes** | `/frentes` | `/frentes/{id}` | `membros` |
| **eventos** | `/eventos` | `/eventos/{id}` | `deputados`, `orgaos`, `pauta`, `votacoes` |
| **órgãos** | `/orgaos` | `/orgaos/{id}` | `eventos`, `membros`, `votacoes` |
| **legislaturas** | `/legislaturas` | `/legislaturas/{id}` | `lideres`, `mesa` |
| **proposições** | `/proposicoes` | `/proposicoes/{id}` | `autores`, `relacionadas`, `temas`, `tramitacoes`, `votacoes` |
| **votações** | `/votacoes` | `/votacoes/{id}` | `orientacoes`, `votos` |
| **referências** | `/referencias/...` | — | tabelas de domínio (tipos, situações, UFs) |

> Detalhes de cada grupo, campos retornados e filtros: veja `references/endpoints.md`.
> Parâmetros de consulta completos: `references/parametros.md`.
> Tabelas de referência (`/referencias`): `references/referencias.md`.
> Receitas prontas (Python/curl) por objetivo: `references/exemplos.md`.

## Como escolher o endpoint (decisão rápida)

- Quer **quem é** o parlamentar → `/deputados` (+ `/{id}` para detalhe completo).
- Quer **gastos** (CEAP) → `/deputados/{id}/despesas?ano=YYYY` (fan-out, por ano).
- Quer **bancadas temáticas** → `/frentes` + `/frentes/{id}/membros`.
- Quer **agenda/sessões** e presença → `/eventos` + `/eventos/{id}/deputados`.
- Quer **comissões/CPIs** → `/orgaos` (filtre por tipo) + `/orgaos/{id}/votacoes|eventos`.
- Quer **como votaram** → `/votacoes` + `/votacoes/{id}/votos` (+ `/orientacoes` para
  a orientação de cada bancada).
- Quer **leis/PLs e tramitação** → `/proposicoes` + `/proposicoes/{id}/tramitacoes`.
- Não sabe o código de um tipo/situação → consulte `/referencias/...` primeiro.

## Armadilhas conhecidas

- **`votacao_votos` traz um objeto `deputado` aninhado** dentro de cada voto — achate-o
  (id/nome/siglaPartido/siglaUf) antes de modelar.
- Alguns endpoints **filho** não paginam (retornam tudo de uma vez) — trate `dados`
  podendo ser objeto único, não lista.
- `id` de proposição/votação pode ser grande; votação usa id string (ex.: `"2265603-43"`).
- `dataFim` em órgãos/eventos pode ser **nulo** (ativo/agendado).
- Filtros de data sem `idLegislatura` podem varrer um volume enorme — combine filtros.
