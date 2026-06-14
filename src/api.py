"""Cliente HTTP da API da Câmara dos Deputados.

Responsabilidade única: buscar com robustez (retry, backoff, paginação).
Não conhece regra de negócio — só fala HTTP.

Paginação: seguimos o array `links` (rel="next") do CORPO da resposta,
que é sempre presente e mais confiável que o header HTTP `Link`.
"""
import time
import logging
import requests

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "ftk-camara/0.1",   # boa prática: se identifica para o servidor
}

log = logging.getLogger(__name__)


class CamaraAPIError(Exception):
    """Erro próprio do cliente — facilita capturar só o que é nosso."""
    pass


def get_json(path, params=None, retries=3, backoff=1.5):
    """Faz GET com retry em erros transitórios (429/5xx) e backoff exponencial."""
    url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
    last_err = None

    for attempt in range(retries):
        try:
            r = requests.get(url, headers=DEFAULT_HEADERS, params=params, timeout=30)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 500, 502, 503, 504):   # transitórios: vale retry
                wait = backoff ** attempt                     # 1, 1.5, 2.25...
                log.warning("status %d em %s, retry em %.1fs", r.status_code, url, wait)
                time.sleep(wait)
                last_err = f"HTTP {r.status_code}"
                continue
            # outros erros (4xx) são definitivos: não insiste
            raise CamaraAPIError(f"HTTP {r.status_code} em {url}: {r.text[:200]}")
        except requests.RequestException as e:                # erro de rede (timeout, DNS...)
            log.warning("erro de rede em %s: %s", url, e)
            time.sleep(backoff ** attempt)
            last_err = str(e)

    raise CamaraAPIError(f"falhou após {retries} tentativas em {url}: {last_err}")


def has_next_page(body):
    """True se a resposta indica próxima página (links[rel=next] no corpo)."""
    return any(link.get("rel") == "next" for link in body.get("links", []))


def iter_pages(path, params=None, max_pages=None):
    """Itera páginas de um endpoint paginado.

    Yields tuplas (lista_de_registros, numero_da_pagina, url_de_origem).
    Para quando não há mais `rel="next"` no corpo, ou ao atingir max_pages.
    """
    params = dict(params or {})   # cópia: não muta o dict do chamador
    page = 1

    while True:
        if max_pages and page > max_pages:
            break

        params["pagina"] = page
        r = get_json(path, params=params)
        body = r.json()
        records = body.get("dados", [])        # a Câmara aninha a lista em "dados"

        if isinstance(records, dict):          # alguns endpoints retornam objeto, não lista
            records = [records]

        yield records, page, r.url

        if not has_next_page(body):            # condição de parada vem do corpo
            break

        page += 1
        time.sleep(0.25)   # rate limit básico: respeita a fonte, evita 429