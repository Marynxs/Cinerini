"""Infraestrutura dos testes.

Cada teste roda dentro de uma transação que é desfeita ao final. Isso permite
executar a suíte contra o mesmo banco de desenvolvimento sem destruir os
dados semeados — o avaliador roda os testes e continua com o cenário
intacto para percorrer o fluxo.
"""

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from app.db import engine, get_db
from app.main import app
from app.models import Event, EventStatus, Role, Room, Showing, User, Venue
from app.ratelimit import clear_all
from app.security import hash_password
from app.seating import generate_seats

SENHA = "senhaDeTeste123"


@pytest.fixture(scope="session")
def connection() -> Iterator[Connection]:
    conn = engine.connect()
    yield conn
    conn.close()


@pytest.fixture
def db(connection: Connection) -> Iterator[Session]:
    """Sessão isolada: tudo que o teste gravar é descartado no fim.

    A transação externa nunca é confirmada. O modo de savepoint permite que
    o código sob teste chame commit() normalmente — o commit vira um
    savepoint dentro da transação externa, que é desfeita depois.
    """
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    outer.rollback()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_rate_limits() -> None:
    """As janelas vivem em memória e sobrevivem entre testes."""
    clear_all()


# --------------------------------------------------------------- cenário


@pytest.fixture
def users(db: Session) -> dict[str, User]:
    criados = {
        "organizer": User(name="Org", email="org@cinerini.com.br",
                          password_hash=hash_password(SENHA), role=Role.ORGANIZER),
        "organizer2": User(name="Org 2", email="org2@cinerini.com.br",
                           password_hash=hash_password(SENHA), role=Role.ORGANIZER),
        "customer": User(name="Cliente", email="cli@cinerini.com.br",
                         password_hash=hash_password(SENHA), role=Role.CUSTOMER),
        "customer2": User(name="Cliente 2", email="cli2@cinerini.com.br",
                          password_hash=hash_password(SENHA), role=Role.CUSTOMER),
        # Sem cinema aqui: quem precisa de portaria pronta usa a fixture
        # `gate_bound`, e assim os testes de cadastro incompleto continuam
        # tendo um caso real para exercitar.
        "gate": User(name="Portaria", email="port@cinerini.com.br",
                     password_hash=hash_password(SENHA), role=Role.GATE),
    }
    db.add_all(criados.values())
    db.commit()
    return criados


@pytest.fixture
def auth(client: TestClient, users: dict[str, User]):
    """Devolve o cabeçalho de autorização de um papel."""

    def _auth(papel: str) -> dict[str, str]:
        r = client.post("/auth/login",
                        json={"email": users[papel].email, "password": SENHA})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _auth


@pytest.fixture
def room(db: Session) -> Room:
    venue = Venue(name="Cine Teste", city="São Paulo", city_ibge_id=3550308,
                  state="SP",
                  address="Rua de Teste, 1")
    db.add(venue)
    db.flush()

    sala = Room(venue_id=venue.id, name="Sala 1", rows=3, seats_per_row=4)
    db.add(sala)
    db.commit()
    return sala


@pytest.fixture
def gate_hired(db: Session, users: dict[str, User], room: Room) -> User:
    """Funcionário com cinema definido, mas ainda sem turno escolhido.

    É o estado em que uma conta nasce: o organizador diz onde a pessoa
    trabalha, e escolher a sessão é o primeiro gesto dela (D24).
    """
    users["gate"].gate_venue_id = room.venue_id
    db.commit()
    return users["gate"]


@pytest.fixture
def showing(db: Session, users: dict[str, User], room: Room) -> Showing:
    """Sessão publicada com 12 assentos gerados."""
    event = Event(organizer_id=users["organizer"].id, title="Filme de Teste",
                  status=EventStatus.PUBLISHED)
    db.add(event)
    db.flush()

    s = Showing(event_id=event.id, room_id=room.id, price_cents=3200,
                starts_at=datetime.now(timezone.utc) + timedelta(days=1))
    db.add(s)
    db.flush()
    generate_seats(db, s)
    db.commit()
    return s


@pytest.fixture
def fake_tmdb(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita rede nos testes: chamada externa é lenta e instável.

    A integração real com o TMDb é exercitada pelo seed, não pela suíte.
    """
    from app import tmdb

    def _request(path: str, params: dict) -> dict:
        if path.startswith("/search"):
            return {"results": [{
                "id": 693134,
                "title": "Duna: Parte Dois",
                "release_date": "2024-02-27",
                "overview": "Paul Atreides se une aos Fremen.",
                "poster_path": "/poster.jpg",
            }]}

        # Devolve o id que foi pedido, em vez de um fixo. O duplo anterior
        # respondia sempre 693134, o que o fazia mentir: dois filmes
        # diferentes voltavam como o mesmo, e nenhum teste conseguia
        # exercitar a regra de um filme por evento (D30).
        pedido = int(path.rsplit("/", 1)[-1])
        titulos = {
            693134: "Duna: Parte Dois",
            27205: "A Origem",
            157336: "Interestelar",
            603: "Matrix",
        }

        return {
            "id": pedido,
            "title": titulos.get(pedido, f"Filme {pedido}"),
            "overview": "Sinopse de teste.",
            "poster_path": "/poster.jpg",
            "backdrop_path": "/backdrop.jpg",
            "runtime": 167,
        }

    monkeypatch.setattr(tmdb, "_request", _request)
    monkeypatch.setattr(tmdb.get_settings(), "tmdb_api_key", "chave-de-teste")
    tmdb.clear_cache()
