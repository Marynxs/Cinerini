"""Cliente do TMDb: cache e tratamento de falha externa."""

import time
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import tmdb
from app.tmdb import TTLCache


class TestTTLCache:
    def test_stores_and_returns(self) -> None:
        c = TTLCache(ttl=60, max_entries=10)
        c.set("a", [1, 2])
        assert c.get("a") == [1, 2]

    def test_missing_key_returns_none(self) -> None:
        assert TTLCache(ttl=60, max_entries=10).get("ausente") is None

    def test_entry_expires(self) -> None:
        c = TTLCache(ttl=1, max_entries=10)
        c.set("a", "v")
        time.sleep(1.1)
        assert c.get("a") is None

    def test_expired_entry_is_removed(self) -> None:
        c = TTLCache(ttl=1, max_entries=10)
        c.set("a", "v")
        time.sleep(1.1)
        c.get("a")
        assert len(c._data) == 0

    def test_respects_the_cap(self) -> None:
        """A chave vem do texto digitado: sem teto, cresce sem fim."""
        c = TTLCache(ttl=60, max_entries=3)
        for i in range(10):
            c.set(f"k{i}", i)
        assert len(c._data) == 3

    def test_discards_least_recently_used(self) -> None:
        c = TTLCache(ttl=60, max_entries=3)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)

        c.get("a")      # 'a' passa a ser a mais recente
        c.set("d", 4)   # deve descartar 'b'

        assert c.get("a") == 1
        assert c.get("b") is None


class TestSearch:
    def test_organizer_gets_results(
        self, client: TestClient, auth, fake_tmdb
    ) -> None:
        r = client.get("/catalog/search", params={"q": "duna"},
                       headers=auth("organizer"))
        assert r.status_code == 200
        assert r.json()[0]["tmdb_id"] == 693134

    def test_poster_comes_as_full_url(
        self, client: TestClient, auth, fake_tmdb
    ) -> None:
        r = client.get("/catalog/search", params={"q": "duna"},
                       headers=auth("organizer"))
        assert r.json()[0]["poster_url"].startswith("https://image.tmdb.org/")

    def test_short_query_is_rejected(
        self, client: TestClient, auth, fake_tmdb
    ) -> None:
        r = client.get("/catalog/search", params={"q": "d"},
                       headers=auth("organizer"))
        assert r.status_code == 422

    def test_anonymous_access_is_refused(self, client: TestClient) -> None:
        """Aberta, a rota viraria proxy gratuito para o TMDb com a nossa chave."""
        assert client.get("/catalog/search",
                          params={"q": "duna"}).status_code == 401


class TestCacheBehaviour:
    def test_repeated_search_does_not_call_again(self, fake_tmdb) -> None:
        chamadas = {"n": 0}
        original = tmdb._request

        def contando(path, params):
            chamadas["n"] += 1
            return original(path, params)

        tmdb._request = contando
        try:
            tmdb.search_movies("duna")
            tmdb.search_movies("duna")
            assert chamadas["n"] == 1
        finally:
            tmdb._request = original

    def test_key_is_normalised(self, fake_tmdb) -> None:
        assert tmdb.search_movies(" DUNA ") == tmdb.search_movies("duna")


class TestExternalFailure:
    """Falha de serviço externo não pode virar 500 genérico: a mensagem
    precisa dizer a quem está cadastrando que o problema é lá fora."""

    @staticmethod
    def _com_chave(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            tmdb, "get_settings",
            lambda: SimpleNamespace(tmdb_api_key="chave-de-teste"),
        )

    def test_network_error_becomes_502(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._com_chave(monkeypatch)
        monkeypatch.setattr(
            tmdb.httpx, "get",
            lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("sem rede")),
        )

        with pytest.raises(HTTPException) as erro:
            tmdb._request("/search/movie", {})
        assert erro.value.status_code == 502

    def test_upstream_error_becomes_502(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._com_chave(monkeypatch)
        monkeypatch.setattr(
            tmdb.httpx, "get",
            lambda *a, **k: httpx.Response(500, json={}),
        )

        with pytest.raises(HTTPException) as erro:
            tmdb._request("/search/movie", {})
        assert erro.value.status_code == 502

    def test_unknown_movie_becomes_404(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._com_chave(monkeypatch)
        monkeypatch.setattr(
            tmdb.httpx, "get",
            lambda *a, **k: httpx.Response(404, json={}),
        )

        with pytest.raises(HTTPException) as erro:
            tmdb._request("/movie/1", {})
        assert erro.value.status_code == 404

    def test_missing_key_becomes_503(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Configuração ausente é indisponibilidade, não erro do cliente."""
        monkeypatch.setattr(
            tmdb, "get_settings", lambda: SimpleNamespace(tmdb_api_key=""),
        )

        with pytest.raises(HTTPException) as erro:
            tmdb._request("/search/movie", {})
        assert erro.value.status_code == 503
