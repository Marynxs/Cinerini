from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    auth, bookings, catalog, events, gate, sharing, showings, venues,
)

settings = get_settings()

app = FastAPI(
    title="Cinerini",
    description="Plataforma de eventos e ingressos.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(venues.router)
app.include_router(events.router)
app.include_router(showings.router)
app.include_router(bookings.router)
app.include_router(sharing.router)
app.include_router(gate.router)


@app.get("/", tags=["infra"], summary="Porta de entrada da API")
def raiz() -> dict[str, str]:
    """Existe porque a raiz de um serviço é o que as pessoas digitam.

    Sem esta rota, abrir o endereço da API devolvia `404 Not Found`, tecnicamente
    correto e inútil: quem chegou ali não sabe se errou o endereço, se o
    serviço caiu, ou se é assim mesmo. Este corpo diz o que é e para onde ir.

    Não redireciona para `/docs` de propósito: redirecionar esconderia que a
    raiz não serve interface, e quem estivesse conferindo o serviço por
    script receberia um 307 no lugar de uma resposta.
    """
    return {
        "servico": "API do Cinerini",
        "documentacao": "/docs",
        "contrato": "/openapi.json",
        "saude": "/health",
        "site": "https://cinerini.vercel.app",
    }


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
