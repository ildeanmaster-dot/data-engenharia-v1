# Receitas prontas — API Câmara v2

Exemplos práticos em `curl` e Python. Todos usam a base
`https://dadosabertos.camara.leg.br/api/v2`.

## Paginação genérica (Python)
```python
import requests, time

BASE = "https://dadosabertos.camara.leg.br/api/v2"

def iter_pages(path, params=None):
    params = dict(params or {}); params.setdefault("itens", 100)
    url = f"{BASE}{path}"
    while url:
        r = requests.get(url, params=params, timeout=30,
                         headers={"Accept": "application/json"})
        r.raise_for_status()
        body = r.json()
        yield from body["dados"]
        # segue o link rel="next" do corpo (mais confiável que montar a URL)
        nxt = next((l["href"] for l in body["links"] if l["rel"] == "next"), None)
        url, params = nxt, None   # o href do next já traz os params
        time.sleep(0.25)          # rate limit educado
```

## Lista de deputados da legislatura atual
```bash
curl "https://dadosabertos.camara.leg.br/api/v2/deputados?idLegislatura=57&itens=100"
```

## Despesas (CEAP) de um deputado, por ano
```bash
curl "https://dadosabertos.camara.leg.br/api/v2/deputados/204379/despesas?ano=2025&itens=100"
```
```python
gastos = list(iter_pages("/deputados/204379/despesas", {"ano": 2025}))
```

## Frentes e seus membros (fan-out)
```python
frentes = list(iter_pages("/frentes", {"idLegislatura": 57}))
for f in frentes[:30]:
    membros = list(iter_pages(f"/frentes/{f['id']}/membros"))
    # ... associe membros à frente f['id']
```

## Eventos de um período + presença
```bash
curl "https://dadosabertos.camara.leg.br/api/v2/eventos?dataInicio=2025-01-01&dataFim=2025-03-31&itens=100"
curl "https://dadosabertos.camara.leg.br/api/v2/eventos/{idEvento}/deputados"
```

## Votações + voto individual (achatar deputado aninhado)
```python
votacoes = list(iter_pages("/votacoes", {"dataInicio": "2025-01-01", "dataFim": "2025-12-31"}))
for v in votacoes[:30]:
    for voto in iter_pages(f"/votacoes/{v['id']}/votos"):
        dep = voto.get("deputado_", {})          # objeto aninhado!
        registro = {
            "id_votacao": v["id"],
            "id_deputado": dep.get("id"),
            "nome_deputado": dep.get("nome"),
            "sigla_partido": dep.get("siglaPartido"),
            "tipo_voto": voto.get("tipoVoto"),
        }
```

## Proposições (PLs de um ano) + tramitação
```bash
curl "https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ano=2025&itens=100"
curl "https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id}/tramitacoes"
```

## Achar CPIs
```bash
# 1) descubra o código do tipo de órgão (comissão temporária / CPI)
curl "https://dadosabertos.camara.leg.br/api/v2/referencias/orgaos/tiposOrgao"
# 2) liste órgãos desse tipo (ou filtre nome/apelido contendo "CPI")
curl "https://dadosabertos.camara.leg.br/api/v2/orgaos?idTipoOrgao={cod}&itens=100"
```

---

## Mapa: entregável do desafio → endpoints
| Entregável | Endpoints |
|---|---|
| Atlas das frentes (HHI) | `/frentes`, `/frentes/{id}/membros`, `/deputados` |
| Calendário de eventos / presença | `/eventos`, `/eventos/{id}/deputados`, `/orgaos` |
| Correlação frentes × votações | `/frentes/{id}/membros`, `/votacoes`, `/votacoes/{id}/votos` |
| Raio-X CEAP (anomalias) | `/deputados`, `/deputados/{id}/despesas` |
| Auditoria de CPIs | `/orgaos` (tipo CPI), `/orgaos/{id}/eventos|votacoes`, `/proposicoes` |
| Score de engajamento | `/eventos/{id}/deputados`, `/votacoes/{id}/votos`, `/deputados/{id}/discursos` |
| (Opcional) CDC de tramitação | `/proposicoes`, `/proposicoes/{id}/tramitacoes` |
