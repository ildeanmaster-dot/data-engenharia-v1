# Parâmetros de consulta — API Câmara v2

## Paginação e ordenação (valem para quase todas as listas)
| Parâmetro | Valores | Notas |
|---|---|---|
| `pagina` | inteiro ≥ 1 | default 1 |
| `itens` | 1–100 | **máximo 100** (default 15). Use 100 na ingestão |
| `ordem` | `ASC` / `DESC` | sentido da ordenação |
| `ordenarPor` | nome de campo | ex.: `nome`, `id`, `ano`, `sigla`, `dataApresentacao` |
| `formato` | `json` / `xml` | default `json` (ou use header `Accept`) |

A resposta traz a paginação em `links`:
```
rel="self"  -> a página atual
rel="first" -> primeira página
rel="last"  -> última página (dá pra estimar o total)
rel="next"  -> próxima (ausente na última)
rel="prev"  -> anterior (ausente na primeira)
```
Há também o header HTTP `Link` com o mesmo conteúdo. **Para paginar, siga `rel="next"`
até ele não existir mais.**

## Filtros mais usados por grupo
| Grupo | Filtros comuns |
|---|---|
| deputados | `siglaUf`, `siglaPartido`, `siglaSexo`, `idLegislatura`, `nome` |
| despesas (CEAP) | `ano`, `mes`, `cnpjCpfFornecedor` |
| frentes / blocos / partidos | `idLegislatura`, `sigla` |
| eventos | `dataInicio`, `dataFim`, `idTipoEvento`, `idOrgao` |
| órgãos | `idTipoOrgao`, `dataInicio`, `dataFim` |
| proposições | `siglaTipo`, `numero`, `ano`, `idDeputadoAutor`, `keywords`, `codTema`, `dataApresentacaoInicio/Fim` |
| votações | `dataInicio`, `dataFim`, `idOrgao`, `idProposicao`, `idEvento` |

## Formatos de data
- **Filtro:** `AAAA-MM-DD` (ex.: `dataInicio=2025-01-01`).
- **Timestamp na resposta:** `AAAA-MM-DDTHH:MM` (ex.: `2026-06-12T14:30`).
- Sem timezone explícito; trate como horário de Brasília ao normalizar.

## Multivalor
Vários filtros aceitam repetição para "OU":
`?siglaUf=SP&siglaUf=RJ` → deputados de SP **ou** RJ.

## Boas práticas de filtro
- Combine `idLegislatura=57` com filtros de data para limitar volume.
- Em proposições, sempre filtre por `siglaTipo`+`ano` (o acervo total é gigante:
  dezenas de milhares de páginas).
- Use `/referencias` para descobrir os códigos válidos antes de filtrar por `codTipo`,
  `idTipoEvento`, `idTipoOrgao`, `codSituacao`, etc.
