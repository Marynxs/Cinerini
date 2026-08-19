"""Cliente do TMDb.

O catálogo do cliente não passa por aqui: título, sinopse, pôster e duração
são copiados para a tabela events na publicação. Este módulo serve apenas ao
organizador, enquanto ele procura o filme, e por isso o cache é modesto.
"""

import time
from collections import OrderedDict
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.config import get_settings

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p"

# Quem limita a memória é o teto de entradas, não o prazo. O prazo é rede de
# segurança contra um processo de vida longa servir catálogo antigo: sem ele,
# o LRU manteria uma busca popular em memória indefinidamente. Seis horas
# atravessam uma jornada do organizador sem expirar nada e ainda renovam o
# catálogo algumas vezes por dia. Prazo curto aqui só descartaria cache útil,
# já que sinopse e pôster de filme lançado praticamente não mudam.
CACHE_TTL_SECONDS = 6 * 60 * 60
CACHE_MAX_ENTRIES = 200


class TTLCache:
    """Cache com prazo e teto de entradas.

    O teto existe porque a chave vem da busca digitada pelo usuário: sem
    limite, termos aleatórios fariam o dicionário crescer sem fim. Expirar
    por tempo não basta, porque entrada que ninguém consulta de novo nunca seria
    removida.
    """

    def __init__(self, ttl: int, max_entries: int) -> None:
        self.ttl = ttl
        self.max_entries = max_entries
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        item = self._data.get(key)
        if item is None:
            return None

        stored_at, value = item
        if time.monotonic() - stored_at > self.ttl:
            del self._data[key]
            return None

        self._data.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        self._data[key] = (time.monotonic(), value)
        self._data.move_to_end(key)
        while len(self._data) > self.max_entries:
            # Descarta a entrada menos recentemente usada.
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()


_cache = TTLCache(CACHE_TTL_SECONDS, CACHE_MAX_ENTRIES)


def image_url(path: str | None, size: str) -> str | None:
    return f"{IMAGE_BASE}/{size}{path}" if path else None


def _request(path: str, params: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    if not settings.tmdb_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Catálogo externo não configurado.",
        )

    try:
        response = httpx.get(
            f"{BASE_URL}{path}",
            params={"api_key": settings.tmdb_api_key,
                    "language": "pt-BR", **params},
            timeout=8,
        )
    except httpx.RequestError:
        # Falha de rede não deve virar 500: o problema é de um serviço
        # externo, e a mensagem precisa dizer isso a quem está cadastrando.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível consultar o catálogo agora. Tente de novo.",
        )

    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filme não encontrado no catálogo.",
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="O catálogo externo respondeu com erro.",
        )

    return response.json()


def search_movies(query: str, page: int = 1) -> list[dict[str, Any]]:
    # Normaliza a chave para que "Duna", "duna " e " DUNA" compartilhem a
    # mesma entrada em vez de ocuparem três.
    key = f"search:{query.strip().lower()}:{page}"

    cached = _cache.get(key)
    if cached is not None:
        return cached

    data = _request("/search/movie", {"query": query.strip(), "page": page})
    results = [
        {
            "tmdb_id": m["id"],
            "title": m.get("title") or m.get("original_title", ""),
            "year": (m.get("release_date") or "")[:4] or None,
            "synopsis": m.get("overview") or None,
            "poster_url": image_url(m.get("poster_path"), "w342"),
        }
        for m in data.get("results", [])
    ]

    _cache.set(key, results)
    return results


def movie_details(tmdb_id: int) -> dict[str, Any]:
    key = f"movie:{tmdb_id}"

    cached = _cache.get(key)
    if cached is not None:
        return cached

    data = _request(f"/movie/{tmdb_id}", {})
    details = {
        "tmdb_id": data["id"],
        "title": data.get("title") or data.get("original_title", ""),
        "synopsis": data.get("overview") or None,
        "poster_url": image_url(data.get("poster_path"), "w500"),
        "backdrop_url": image_url(data.get("backdrop_path"), "w1280"),
        "runtime_minutes": data.get("runtime") or None,
    }

    _cache.set(key, details)
    return details


def clear_cache() -> None:
    """Zera o cache. Usado por testes."""
    _cache.clear()
