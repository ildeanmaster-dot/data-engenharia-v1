# Tabelas de referência — `/referencias/...`

As tabelas de referência traduzem **códigos em descrições** e listam os **valores válidos**
de muitos filtros. Consulte-as antes de filtrar por código ou para enriquecer dimensões.

Padrão de uso: `GET /referencias/<tabela>` → retorna `{ "dados": [ {cod, nome/sigla, ...} ] }`.

## Principais tabelas

| Caminho | Para que serve |
|---|---|
| `/referencias/deputados/siglaUf` | UFs válidas |
| `/referencias/deputados/siglaSexo` | M / F |
| `/referencias/deputados/tipoDespesa` | categorias da CEAP (combustível, divulgação, passagens...) |
| `/referencias/proposicoes/siglaTipo` | tipos de proposição (PL, PEC, MPV, PDL, REQ...) e seus `cod` |
| `/referencias/proposicoes/codTema` | temas para o filtro `codTema` |
| `/referencias/proposicoes/codSituacao` | situações de tramitação |
| `/referencias/tiposTramitacao` | tipos de movimentação na tramitação |
| `/referencias/situacoesProposicao` | estados possíveis de uma proposição |
| `/referencias/eventos/tiposEvento` | tipos de evento (sessão, audiência, seminário...) |
| `/referencias/eventos/situacoesEvento` | situações (agendado, realizado, cancelado...) |
| `/referencias/orgaos/tiposOrgao` | tipos de órgão (comissão permanente, temporária/CPI, conselho...) |
| `/referencias/orgaos/situacoesOrgao` | situações do órgão |
| `/referencias/situacoesDeputado` | situações de mandato |

## Exemplos de quando usar
- Para achar **CPIs**: descubra em `/referencias/orgaos/tiposOrgao` o código do tipo
  "comissão temporária"/CPI e filtre `/orgaos?idTipoOrgao=<cod>` (ou filtre por `nome`/`apelido` contendo "CPI").
- Para listar só **PLs de 2025**: confirme em `/referencias/proposicoes/siglaTipo` que
  `PL` existe e use `/proposicoes?siglaTipo=PL&ano=2025`.
- Para classificar **gastos da CEAP**: junte `tipoDespesa` com a tabela
  `/referencias/deputados/tipoDespesa` para padronizar categorias.

> Os nomes exatos de algumas tabelas podem variar; se um caminho retornar vazio,
> liste `/referencias` (raiz) para ver os disponíveis.
