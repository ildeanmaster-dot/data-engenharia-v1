# Endpoints detalhados — API Câmara v2

Base: `https://dadosabertos.camara.leg.br/api/v2`. Toda lista retorna `{ "dados": [...], "links": [...] }`.

---

## deputados
- `GET /deputados` — lista. Filtros: `id`, `nome`, `siglaUf`, `siglaPartido`, `siglaSexo`, `idLegislatura`, `dataNascimento`, `ordem`, `ordenarPor`.
  - Campos: `id`, `uri`, `nome`, `siglaPartido`, `uriPartido`, `siglaUf`, `idLegislatura`, `urlFoto`, `email`.
- `GET /deputados/{id}` — detalhe completo: nome civil, CPF (parcial), gabinete, redes, escolaridade, data/UF de nascimento.
- `GET /deputados/{id}/despesas` — **CEAP** (cota parlamentar). Filtros: `ano`, `mes`, `cnpjCpfFornecedor`, `idLegislatura`, `ordem`, `ordenarPor`. Paginado.
  - Campos: `ano`, `mes`, `tipoDespesa`, `codDocumento`, `tipoDocumento`, `dataDocumento`, `numDocumento`, `valorDocumento`, `valorLiquido`, `valorGlosa`, `nomeFornecedor`, `cnpjCpfFornecedor`, `urlDocumento`.
- `GET /deputados/{id}/discursos` — discursos. Filtros por data e `ordenarPor`.
- `GET /deputados/{id}/eventos` — eventos de que participou.
- `GET /deputados/{id}/frentes` — frentes que integra.
- `GET /deputados/{id}/orgaos` — comissões/órgãos de que é membro.
- `GET /deputados/{id}/historico` · `/ocupacoes` · `/profissoes` · `/mandatosExternos`.

## partidos
- `GET /partidos` — Filtros: `sigla`, `idLegislatura`, `ordem`, `ordenarPor`. Campos: `id`, `sigla`, `nome`, `uri`.
- `GET /partidos/{id}` — detalhe: líder atual, situação, total de membros, logo.
- `GET /partidos/{id}/membros` — deputados do partido.
- `GET /partidos/{id}/lideres` — liderança.

## blocos
- `GET /blocos` — blocos partidários (coligações de bancada). Filtro: `idLegislatura`.
- `GET /blocos/{id}` — detalhe.

## frentes
- `GET /frentes` — frentes parlamentares. Filtro: `idLegislatura`. Campos: `id`, `titulo`, `idLegislatura`, `uri`.
- `GET /frentes/{id}` — detalhe: telefone, situação, coordenador, total de membros.
- `GET /frentes/{id}/membros` — composição. Campos: `id` (deputado), `nome`, `siglaPartido`, `siglaUf`, `titulo` (papel na frente), `codTitulo`.

## eventos
- `GET /eventos` — sessões, audiências, reuniões. Filtros: `dataInicio`, `dataFim`, `idTipoEvento`, `idOrgao`, `ordem`, `ordenarPor`.
  - Campos: `id`, `dataHoraInicio`, `dataHoraFim`, `situacao`, `descricaoTipo`, `descricao`, `localCamara`, `orgaos`.
- `GET /eventos/{id}` — detalhe.
- `GET /eventos/{id}/deputados` — **presença** (quem participou).
- `GET /eventos/{id}/orgaos` — órgãos promotores.
- `GET /eventos/{id}/pauta` — pauta (proposições previstas).
- `GET /eventos/{id}/votacoes` — votações realizadas no evento.

## órgãos
- `GET /orgaos` — comissões, conselhos, mesa, **CPIs**. Filtros: `idTipoOrgao`, `dataInicio`, `dataFim`, `ordem`, `ordenarPor`.
  - Campos: `id`, `sigla`, `nome`, `apelido`, `codTipoOrgao`, `tipoOrgao`, `nomePublicacao`, `dataInicio`, `dataFim`.
  - 💡 CPIs: filtre por tipo de órgão de comissão temporária / use o `nome`/`apelido` contendo "CPI".
- `GET /orgaos/{id}` — detalhe.
- `GET /orgaos/{id}/membros` — composição (com cargo).
- `GET /orgaos/{id}/eventos` — reuniões do órgão.
- `GET /orgaos/{id}/votacoes` — votações no órgão.

## legislaturas
- `GET /legislaturas` — períodos legislativos (a 57 é a atual). Filtros por data.
- `GET /legislaturas/{id}` — detalhe (dataInicio/dataFim).
- `GET /legislaturas/{id}/lideres` · `/mesa` — liderança e mesa diretora do período.

## proposições
- `GET /proposicoes` — PLs, PECs, MPVs, etc. Filtros: `siglaTipo`, `numero`, `ano`, `idDeputadoAutor`, `autor`, `siglaUfAutor`, `siglaPartidoAutor`, `keywords`, `codTema`, `dataApresentacaoInicio`, `dataApresentacaoFim`, `ordem`, `ordenarPor`.
  - Campos: `id`, `siglaTipo`, `codTipo`, `numero`, `ano`, `ementa`, `dataApresentacao`.
- `GET /proposicoes/{id}` — detalhe: ementa completa, status atual, regime, despacho.
- `GET /proposicoes/{id}/autores` — autores (deputados/órgãos).
- `GET /proposicoes/{id}/tramitacoes` — **histórico de tramitação** (ideal para CDC/SCD2).
- `GET /proposicoes/{id}/votacoes` — votações da proposição.
- `GET /proposicoes/{id}/temas` · `/relacionadas`.

## votações
- `GET /votacoes` — Filtros: `dataInicio`, `dataFim`, `idOrgao`, `idProposicao`, `idEvento`, `ordem`, `ordenarPor`.
  - Campos: `id` (string, ex.: `"2265603-43"`), `data`, `dataHoraRegistro`, `siglaOrgao`, `descricao`, `aprovacao`.
- `GET /votacoes/{id}` — detalhe + placar (`votosSim`, `votosNao`, `votosOutros`).
- `GET /votacoes/{id}/votos` — **voto individual** por deputado. Campos: `tipoVoto`, `dataRegistroVoto`, objeto `deputado_` aninhado (id, nome, siglaPartido, siglaUf).
- `GET /votacoes/{id}/orientacoes` — orientação de cada bancada (Sim/Não/Liberado).

## referências
Tabelas de domínio para traduzir códigos e descobrir valores válidos de filtros.
Veja `referencias.md`.
