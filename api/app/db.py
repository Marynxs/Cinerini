from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


# Acima do teto de requisições em andamento (app/backpressure.py), para que
# toda requisição admitida encontre conexão livre. Dez ficam abertas; as
# outras trinta só existem durante um pico.
POOL_SIZE = 10
MAX_OVERFLOW = 30

engine = create_engine(
    get_settings().database_url,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    # Conexão derrubada do lado do banco (manutenção, failover, ociosidade)
    # é descartada antes de ser entregue a uma requisição.
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
