from fastapi import APIRouter, Query

from app.deps import Organizer
from app.schemas import TmdbDetailOut, TmdbSearchOut
from app.tmdb import movie_details, search_movies

# Restrito ao organizador: é a ferramenta de montar evento, não uma vitrine.
# Aberta ao público, exporia a chave do TMDb a uso de terceiros através da
# nossa API.
router = APIRouter(prefix="/catalog", tags=["catálogo externo"])


@router.get("/search", response_model=list[TmdbSearchOut])
def search(
    _: Organizer,
    q: str = Query(min_length=2, max_length=120, description="Título a procurar"),
    page: int = Query(1, ge=1, le=50),
) -> list[TmdbSearchOut]:
    return [TmdbSearchOut(**m) for m in search_movies(q, page)]


@router.get("/movie/{tmdb_id}", response_model=TmdbDetailOut)
def detail(tmdb_id: int, _: Organizer) -> TmdbDetailOut:
    return TmdbDetailOut(**movie_details(tmdb_id))
