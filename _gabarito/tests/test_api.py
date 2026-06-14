"""Smoke tests do cliente HTTP. Usa responses pra mockar a API real."""
import pytest
import responses

from src.api import get_json, parse_next_page, iter_pages, BASE_URL


@responses.activate
def test_get_json_ok():
    responses.add(
        responses.GET,
        f"{BASE_URL}/deputados",
        json={"dados": [{"id": 1, "nome": "Foo"}]},
        status=200,
    )
    r = get_json("/deputados")
    assert r.json()["dados"][0]["id"] == 1


@responses.activate
def test_get_json_retry_em_5xx():
    # falha 2x e funciona na 3a
    for _ in range(2):
        responses.add(responses.GET, f"{BASE_URL}/x", status=503)
    responses.add(responses.GET, f"{BASE_URL}/x", json={"dados": []}, status=200)

    r = get_json("/x", retries=3, backoff=1.01)
    assert r.status_code == 200


def test_parse_next_page():
    h = '<https://api/?pagina=1>; rel="self", <https://api/?pagina=2>; rel="next"'
    assert parse_next_page(h) == "https://api/?pagina=2"

    assert parse_next_page(None) is None
    assert parse_next_page('<https://api/>; rel="self"') is None


@responses.activate
def test_iter_pages_para_em_sem_link():
    responses.add(
        responses.GET,
        f"{BASE_URL}/deputados",
        json={"dados": [{"id": 1}]},
        status=200,
    )
    pages = list(iter_pages("/deputados"))
    assert len(pages) == 1
    records, page_num, _ = pages[0]
    assert page_num == 1
    assert records == [{"id": 1}]
