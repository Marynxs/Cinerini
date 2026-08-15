from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, catalog, events, showings, venues

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


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
