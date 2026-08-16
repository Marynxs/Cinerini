"""Cinemas, salas, eventos, sessões e a geração do mapa de assentos."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Order, OrderStatus, Room, Seat, Showing, Ticket, TicketStatus, User,
)

AMANHA = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
CINEMA = {"name": "Cine Novo", "city": "Curitiba", "state": "PR",
          "address": "Rua XV, 100"}


def _vender(db: Session, showing: Showing, users: dict[str, User]) -> Ticket:
    assento = db.scalars(
        select(Seat).where(Seat.showing_id == showing.id).limit(1)
    ).one()
    pedido = Order(customer_id=users["customer"].id, showing_id=showing.id,
                   total_cents=3200, status=OrderStatus.PAID)
    db.add(pedido)
    db.flush()

    ingresso = Ticket(order_id=pedido.id, seat_id=assento.id,
                      status=TicketStatus.VALID)
    db.add(ingresso)
    db.commit()
    return ingresso


class TestVenues:
    def test_organizer_creates_venue(self, client: TestClient, auth) -> None:
        r = client.post("/venues", json=CINEMA, headers=auth("organizer"))
        assert r.status_code == 201

    def test_state_is_normalised_to_uppercase(
        self, client: TestClient, auth
    ) -> None:
        """'pr' e 'PR' são a mesma UF; as duas formas quebrariam o filtro."""
        r = client.post("/venues", json={**CINEMA, "state": "pr"},
                        headers=auth("organizer"))
        assert r.json()["state"] == "PR"

    def test_same_name_in_same_city_is_rejected(
        self, client: TestClient, auth
    ) -> None:
        client.post("/venues", json=CINEMA, headers=auth("organizer"))
        r = client.post("/venues", json=CINEMA, headers=auth("organizer"))
        assert r.status_code == 409

    @pytest.mark.parametrize("papel", ["customer", "gate"])
    def test_only_organizer_creates(
        self, client: TestClient, auth, papel: str
    ) -> None:
        r = client.post("/venues", json=CINEMA, headers=auth(papel))
        assert r.status_code == 403

    def test_listing_is_public(self, client: TestClient, room: Room) -> None:
        assert client.get("/venues").status_code == 200

    def test_city_filter(self, client: TestClient, room: Room) -> None:
        assert client.get("/venues",
                          params={"city": "São Paulo"}).json()[0]["city"] == "São Paulo"

    def test_cities_feed_the_catalog_filter(
        self, client: TestClient, room: Room
    ) -> None:
        assert "São Paulo" in client.get("/venues/cities").json()


class TestRooms:
    def test_capacity_is_derived(
        self, client: TestClient, auth, room: Room
    ) -> None:
        r = client.get(f"/venues/{room.venue_id}/rooms")
        assert r.json()[0]["capacity"] == 12

    def test_same_name_in_same_venue_is_rejected(
        self, client: TestClient, auth, room: Room
    ) -> None:
        r = client.post(f"/venues/{room.venue_id}/rooms",
                        json={"name": room.name, "rows": 5, "seats_per_row": 5},
                        headers=auth("organizer"))
        assert r.status_code == 409

    def test_more_rows_than_letters_is_rejected(
        self, client: TestClient, auth, room: Room
    ) -> None:
        """Cada fileira é uma letra de A a Z."""
        r = client.post(f"/venues/{room.venue_id}/rooms",
                        json={"name": "Sala 99", "rows": 27, "seats_per_row": 4},
                        headers=auth("organizer"))
        assert r.status_code == 422

    def test_room_with_showings_cannot_be_deleted(
        self, client: TestClient, auth, showing: Showing, room: Room
    ) -> None:
        r = client.delete(f"/venues/{room.venue_id}/rooms/{room.id}",
                          headers=auth("organizer"))
        assert r.status_code == 409


class TestEvents:
    def test_created_as_draft(self, client: TestClient, auth) -> None:
        r = client.post("/events", json={"title": "Filme Manual"},
                        headers=auth("organizer"))
        assert r.status_code == 201
        assert r.json()["status"] == "draft"

    def test_tmdb_fills_the_details(
        self, client: TestClient, auth, fake_tmdb
    ) -> None:
        """A ficha vem do catálogo: aceitá-la do corpo permitiria publicar
        um filme com dados que não são dele."""
        r = client.post("/events",
                        json={"tmdb_id": 693134, "title": "Título Inventado"},
                        headers=auth("organizer"))
        assert r.json()["title"] == "Duna: Parte Dois"

    def test_without_tmdb_id_or_title_is_rejected(
        self, client: TestClient, auth
    ) -> None:
        assert client.post("/events", json={},
                           headers=auth("organizer")).status_code == 422

    def test_public_catalog_shows_only_published(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        client.post("/events", json={"title": "Rascunho"},
                    headers=auth("organizer"))
        titulos = [e["title"] for e in client.get("/events").json()]
        assert "Rascunho" not in titulos
        assert "Filme de Teste" in titulos


class TestPublishing:
    def _evento_com_sessao(self, client: TestClient, auth, room: Room) -> int:
        evento = client.post("/events", json={"title": "A Publicar"},
                             headers=auth("organizer")).json()
        client.post(f"/events/{evento['id']}/showings",
                    json={"room_id": room.id, "starts_at": AMANHA,
                          "price_cents": 3200},
                    headers=auth("organizer"))
        return evento["id"]

    def test_cannot_publish_without_showings(
        self, client: TestClient, auth
    ) -> None:
        evento = client.post("/events", json={"title": "Vazio"},
                             headers=auth("organizer")).json()
        r = client.post(f"/events/{evento['id']}/publish",
                        headers=auth("organizer"))
        assert r.status_code == 409

    def test_publishing_generates_the_seat_map(
        self, client: TestClient, auth, room: Room
    ) -> None:
        evento_id = self._evento_com_sessao(client, auth, room)
        sessao = client.get(f"/events/{evento_id}/showings").json()[0]

        assert client.get(f"/showings/{sessao['id']}/seats").json() == []

        client.post(f"/events/{evento_id}/publish", headers=auth("organizer"))
        assentos = client.get(f"/showings/{sessao['id']}/seats").json()
        assert len(assentos) == 12

    def test_rows_are_lettered_from_a(
        self, client: TestClient, showing: Showing
    ) -> None:
        assentos = client.get(f"/showings/{showing.id}/seats").json()
        assert {a["row_label"] for a in assentos} == {"A", "B", "C"}

    def test_first_row_has_two_accessible_seats(
        self, client: TestClient, showing: Showing
    ) -> None:
        """Fileira A: piso plano, sem os degraus da arquibancada."""
        assentos = client.get(f"/showings/{showing.id}/seats").json()
        acessiveis = [a for a in assentos if a["kind"] == "accessible"]
        assert len(acessiveis) == 2
        assert all(a["row_label"] == "A" for a in acessiveis)

    def test_publishing_twice_does_not_duplicate_seats(
        self, client: TestClient, auth, room: Room
    ) -> None:
        evento_id = self._evento_com_sessao(client, auth, room)
        sessao = client.get(f"/events/{evento_id}/showings").json()[0]

        client.post(f"/events/{evento_id}/publish", headers=auth("organizer"))
        client.post(f"/events/{evento_id}/publish", headers=auth("organizer"))

        assert len(client.get(f"/showings/{sessao['id']}/seats").json()) == 12

    def test_unpublishing_keeps_seats_and_tickets(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        """Quem comprou continua com ingresso válido; muda a visibilidade."""
        client.post(f"/events/{showing.event_id}/unpublish",
                    headers=auth("organizer"))
        assert len(client.get(f"/showings/{showing.id}/seats").json()) == 12


class TestOwnership:
    """Evento alheio devolve 404, não 403: confirmar a existência permitiria
    mapear o catálogo de outro organizador varrendo ids sequenciais."""

    def test_another_organizer_cannot_publish(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        r = client.post(f"/events/{showing.event_id}/publish",
                        headers=auth("organizer2"))
        assert r.status_code == 404

    def test_another_organizer_cannot_edit_showing(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        r = client.patch(f"/showings/{showing.id}", json={"price_cents": 1},
                         headers=auth("organizer2"))
        assert r.status_code == 404


class TestRoomChange:
    """Decisão D9: a sala trava na primeira venda, não na publicação."""

    @pytest.fixture
    def sala_menor(self, client: TestClient, auth, room: Room) -> dict:
        return client.post(f"/venues/{room.venue_id}/rooms",
                           json={"name": "Sala Menor", "rows": 2,
                                 "seats_per_row": 2},
                           headers=auth("organizer")).json()

    def test_without_sales_the_map_is_rebuilt(
        self, client: TestClient, auth, showing: Showing, sala_menor: dict
    ) -> None:
        r = client.patch(f"/showings/{showing.id}",
                         json={"room_id": sala_menor["id"]},
                         headers=auth("organizer"))
        assert r.status_code == 200
        assert len(client.get(f"/showings/{showing.id}/seats").json()) == 4

    def test_with_sales_the_change_is_refused(
        self, client: TestClient, auth, db: Session, showing: Showing,
        users: dict[str, User], sala_menor: dict,
    ) -> None:
        _vender(db, showing, users)

        r = client.patch(f"/showings/{showing.id}",
                         json={"room_id": sala_menor["id"]},
                         headers=auth("organizer"))
        assert r.status_code == 409
        assert len(client.get(f"/showings/{showing.id}/seats").json()) == 12

    def test_price_stays_editable_after_sales(
        self, client: TestClient, auth, db: Session, showing: Showing,
        users: dict[str, User],
    ) -> None:
        """Promoção é operação corriqueira; quem comprou pagou o registrado."""
        _vender(db, showing, users)

        r = client.patch(f"/showings/{showing.id}", json={"price_cents": 2800},
                         headers=auth("organizer"))
        assert r.status_code == 200

    def test_showing_with_tickets_cannot_be_deleted(
        self, client: TestClient, auth, db: Session, showing: Showing,
        users: dict[str, User],
    ) -> None:
        _vender(db, showing, users)

        r = client.delete(f"/showings/{showing.id}", headers=auth("organizer"))
        assert r.status_code == 409
