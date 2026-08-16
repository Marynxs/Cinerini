"""Reserva, expiração da espera, pagamento e emissão do ingresso."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Order, OrderStatus, Seat, Showing, Ticket, TicketStatus
from app.security import TOKEN_TYPE_TICKET, decode_token

APROVADO = "4111111111111111"
RECUSADO = "4111111111111110"  # termina em zero
PAGAMENTO = {"card_number": APROVADO, "holder_name": "Bruno Tavares"}


@pytest.fixture
def seats(db: Session, showing: Showing) -> list[Seat]:
    return list(db.scalars(
        select(Seat).where(Seat.showing_id == showing.id)
        .order_by(Seat.row_label, Seat.number)
    ))


def _reservar(client: TestClient, auth, showing: Showing, ids: list[int],
              papel: str = "customer"):
    return client.post(f"/showings/{showing.id}/reservations",
                       json={"seat_ids": ids}, headers=auth(papel))


class TestReservation:
    def test_holds_the_chosen_seats(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        r = _reservar(client, auth, showing, [seats[0].id, seats[1].id])

        assert r.status_code == 201
        corpo = r.json()
        assert corpo["status"] == "pending"
        assert len(corpo["tickets"]) == 2
        assert all(t["status"] == "held" for t in corpo["tickets"])

    def test_total_comes_from_the_showing_not_the_request(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        """Aceitar o valor do cliente permitiria comprar por um centavo."""
        r = client.post(f"/showings/{showing.id}/reservations",
                        json={"seat_ids": [seats[0].id], "total_cents": 1},
                        headers=auth("customer"))

        assert r.json()["total_cents"] == showing.price_cents

    def test_total_multiplies_by_seat_count(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        r = _reservar(client, auth, showing, [s.id for s in seats[:3]])
        assert r.json()["total_cents"] == showing.price_cents * 3

    def test_held_seat_shows_as_taken_on_the_map(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        _reservar(client, auth, showing, [seats[0].id])

        mapa = client.get(f"/showings/{showing.id}/seats").json()
        ocupado = next(a for a in mapa if a["id"] == seats[0].id)
        assert ocupado["taken"] is True
        assert sum(1 for a in mapa if a["taken"]) == 1

    def test_seat_from_another_showing_is_rejected(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        outra = Showing(event_id=showing.event_id, room_id=showing.room_id,
                        price_cents=1000,
                        starts_at=datetime.now(timezone.utc) + timedelta(days=2))
        db.add(outra)
        db.commit()

        r = _reservar(client, auth, outra, [seats[0].id])
        assert r.status_code == 409

    def test_duplicate_seat_in_selection_is_rejected(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        r = _reservar(client, auth, showing, [seats[0].id, seats[0].id])
        assert r.status_code == 409

    @pytest.mark.parametrize("papel", ["organizer", "gate"])
    def test_only_customer_reserves(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat],
        papel: str,
    ) -> None:
        assert _reservar(client, auth, showing, [seats[0].id],
                         papel).status_code == 403


class TestReplacingAReservation:
    """Voltar ao mapa e escolher de novo substitui a reserva anterior."""

    def test_new_reservation_frees_the_previous_seats(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        _reservar(client, auth, showing, [seats[0].id])
        _reservar(client, auth, showing, [seats[1].id])

        mapa = client.get(f"/showings/{showing.id}/seats").json()
        primeira = next(a for a in mapa if a["id"] == seats[0].id)
        segunda = next(a for a in mapa if a["id"] == seats[1].id)

        assert primeira["taken"] is False
        assert segunda["taken"] is True

    def test_only_one_open_order_per_showing(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        _reservar(client, auth, showing, [seats[0].id])
        _reservar(client, auth, showing, [seats[1].id])

        pedidos = client.get("/me/orders", headers=auth("customer")).json()
        abertos = [p for p in pedidos
                   if p["showing_id"] == showing.id
                   and p["status"] in ("pending", "refused")]
        assert len(abertos) == 1

    def test_previous_seats_can_be_taken_by_someone_else(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        """Liberar de verdade, e não só marcar: a poltrona volta ao estoque."""
        _reservar(client, auth, showing, [seats[0].id])
        _reservar(client, auth, showing, [seats[1].id])

        outro = _reservar(client, auth, showing, [seats[0].id], "customer2")
        assert outro.status_code == 201

    def test_reservation_of_another_showing_is_untouched(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        outra = Showing(event_id=showing.event_id, room_id=showing.room_id,
                        price_cents=2000,
                        starts_at=datetime.now(timezone.utc) + timedelta(days=3))
        db.add(outra)
        db.flush()
        from app.seating import generate_seats
        generate_seats(db, outra)
        db.commit()

        assentos_outra = db.scalars(
            select(Seat).where(Seat.showing_id == outra.id).limit(1)
        ).all()

        _reservar(client, auth, outra, [assentos_outra[0].id])
        _reservar(client, auth, showing, [seats[0].id])

        pedidos = client.get("/me/orders", headers=auth("customer")).json()
        abertos = [p for p in pedidos if p["status"] == "pending"]
        assert len(abertos) == 2


class TestContention:
    """A garantia central, exercitada por dois clientes de verdade."""

    def test_second_customer_loses_the_same_seat(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        primeiro = _reservar(client, auth, showing, [seats[0].id], "customer")
        assert primeiro.status_code == 201

        segundo = _reservar(client, auth, showing, [seats[0].id], "customer2")
        assert segundo.status_code == 409

    def test_loser_is_told_which_seat_was_lost(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        """Mensagem genérica obrigaria o cliente a adivinhar o que refazer."""
        _reservar(client, auth, showing, [seats[0].id], "customer")

        r = _reservar(client, auth, showing, [seats[0].id, seats[1].id],
                      "customer2")
        assert seats[0].label in r.json()["detail"]["seats"]

    def test_losing_one_seat_does_not_book_the_others(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        """A reserva é tudo ou nada: meia compra deixaria o cliente com um
        assento sozinho sem ter escolhido isso."""
        _reservar(client, auth, showing, [seats[0].id], "customer")
        _reservar(client, auth, showing, [seats[0].id, seats[1].id], "customer2")

        vivos = db.scalars(
            select(Ticket).join(Seat, Ticket.seat_id == Seat.id)
            .where(Seat.id == seats[1].id,
                   Ticket.status != TicketStatus.CANCELLED)
        ).all()
        assert vivos == []


class TestHoldExpiry:
    def _vencer(self, db: Session, order_id: int) -> None:
        for t in db.scalars(select(Ticket).where(Ticket.order_id == order_id)):
            t.held_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    def test_expired_hold_frees_the_seat(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        primeiro = _reservar(client, auth, showing, [seats[0].id], "customer")
        self._vencer(db, primeiro.json()["id"])

        segundo = _reservar(client, auth, showing, [seats[0].id], "customer2")
        assert segundo.status_code == 201

    def test_expired_hold_is_cancelled_not_deleted(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        """A linha preservada mantém o rastro da tentativa abandonada."""
        primeiro = _reservar(client, auth, showing, [seats[0].id], "customer")
        self._vencer(db, primeiro.json()["id"])
        _reservar(client, auth, showing, [seats[0].id], "customer2")

        antigo = db.scalars(
            select(Ticket).where(Ticket.order_id == primeiro.json()["id"])
        ).one()
        assert antigo.status == TicketStatus.CANCELLED

    def test_expired_seat_is_free_on_the_map(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        pedido = _reservar(client, auth, showing, [seats[0].id], "customer")
        self._vencer(db, pedido.json()["id"])

        mapa = client.get(f"/showings/{showing.id}/seats").json()
        assert not any(a["taken"] for a in mapa)

    def test_paying_after_expiry_is_refused(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        pedido = _reservar(client, auth, showing, [seats[0].id], "customer")
        self._vencer(db, pedido.json()["id"])

        r = client.post(f"/orders/{pedido.json()['id']}/payment",
                        json=PAGAMENTO, headers=auth("customer"))
        assert r.status_code == 409


class TestPayment:
    @pytest.fixture
    def pedido(self, client: TestClient, auth, showing: Showing,
               seats: list[Seat]) -> dict:
        return _reservar(client, auth, showing, [seats[0].id]).json()

    def test_approved_payment_issues_the_ticket(
        self, client: TestClient, auth, pedido: dict
    ) -> None:
        r = client.post(f"/orders/{pedido['id']}/payment",
                        json=PAGAMENTO, headers=auth("customer"))

        assert r.status_code == 200
        assert r.json()["approved"] is True
        assert r.json()["order"]["status"] == "paid"
        assert r.json()["order"]["tickets"][0]["status"] == "valid"

    def test_refused_card_does_not_issue(
        self, client: TestClient, auth, pedido: dict
    ) -> None:
        r = client.post(f"/orders/{pedido['id']}/payment",
                        json={**PAGAMENTO, "card_number": RECUSADO},
                        headers=auth("customer"))

        assert r.status_code == 200
        assert r.json()["approved"] is False
        assert r.json()["reason"]
        assert r.json()["order"]["status"] == "refused"

    def test_refusal_keeps_the_seat_held(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat],
        pedido: dict,
    ) -> None:
        """Cartão negado não custa a escolha: a poltrona segue reservada até
        o prazo vencer, para o cliente tentar outro cartão."""
        client.post(f"/orders/{pedido['id']}/payment",
                    json={**PAGAMENTO, "card_number": RECUSADO},
                    headers=auth("customer"))

        mapa = client.get(f"/showings/{showing.id}/seats").json()
        ocupada = next(a for a in mapa if a["id"] == seats[0].id)
        assert ocupada["taken"] is True

        outra = _reservar(client, auth, showing, [seats[0].id], "customer2")
        assert outra.status_code == 409

    def test_another_card_works_after_a_refusal(
        self, client: TestClient, auth, pedido: dict
    ) -> None:
        client.post(f"/orders/{pedido['id']}/payment",
                    json={**PAGAMENTO, "card_number": RECUSADO},
                    headers=auth("customer"))

        segunda = client.post(f"/orders/{pedido['id']}/payment",
                              json=PAGAMENTO, headers=auth("customer"))

        assert segunda.status_code == 200
        assert segunda.json()["approved"] is True
        assert segunda.json()["order"]["status"] == "paid"

    def test_expired_hold_after_refusal_is_refused(
        self, client: TestClient, auth, db: Session, pedido: dict
    ) -> None:
        """O prazo continua valendo: recusa não estende a reserva."""
        client.post(f"/orders/{pedido['id']}/payment",
                    json={**PAGAMENTO, "card_number": RECUSADO},
                    headers=auth("customer"))

        for t in db.scalars(select(Ticket).where(Ticket.order_id == pedido["id"])):
            t.held_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

        r = client.post(f"/orders/{pedido['id']}/payment", json=PAGAMENTO,
                        headers=auth("customer"))
        assert r.status_code == 409

    def test_paying_twice_is_refused(
        self, client: TestClient, auth, pedido: dict
    ) -> None:
        client.post(f"/orders/{pedido['id']}/payment", json=PAGAMENTO,
                    headers=auth("customer"))
        segunda = client.post(f"/orders/{pedido['id']}/payment",
                              json=PAGAMENTO, headers=auth("customer"))
        assert segunda.status_code == 409

    def test_another_customer_cannot_pay_my_order(
        self, client: TestClient, auth, pedido: dict
    ) -> None:
        r = client.post(f"/orders/{pedido['id']}/payment", json=PAGAMENTO,
                        headers=auth("customer2"))
        assert r.status_code == 404

    def test_malformed_card_is_rejected(
        self, client: TestClient, auth, pedido: dict
    ) -> None:
        r = client.post(f"/orders/{pedido['id']}/payment",
                        json={**PAGAMENTO, "card_number": "123"},
                        headers=auth("customer"))
        assert r.status_code == 422


class TestMyTickets:
    @pytest.fixture
    def comprado(self, client: TestClient, auth, showing: Showing,
                 seats: list[Seat]) -> dict:
        pedido = _reservar(client, auth, showing, [seats[0].id]).json()
        client.post(f"/orders/{pedido['id']}/payment", json=PAGAMENTO,
                    headers=auth("customer"))
        return pedido

    def test_lists_only_issued_tickets(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat],
        comprado: dict,
    ) -> None:
        """Reserva não paga ainda não é ingresso."""
        _reservar(client, auth, showing, [seats[5].id])

        ingressos = client.get("/me/tickets", headers=auth("customer")).json()
        assert len(ingressos) == 1

    def test_carries_everything_the_screen_needs(
        self, client: TestClient, auth, comprado: dict
    ) -> None:
        ingresso = client.get("/me/tickets", headers=auth("customer")).json()[0]

        for campo in ("event_title", "venue_name", "room_name", "starts_at",
                      "seat_label", "qr_token", "price_cents"):
            assert ingresso[campo], f"{campo} veio vazio"

    def test_does_not_show_other_customers_tickets(
        self, client: TestClient, auth, comprado: dict
    ) -> None:
        assert client.get("/me/tickets", headers=auth("customer2")).json() == []


class TestTicketToken:
    @pytest.fixture
    def ingresso(self, client: TestClient, auth, showing: Showing,
                 seats: list[Seat]) -> dict:
        pedido = _reservar(client, auth, showing, [seats[0].id]).json()
        client.post(f"/orders/{pedido['id']}/payment", json=PAGAMENTO,
                    headers=auth("customer"))
        return client.get("/me/tickets", headers=auth("customer")).json()[0]

    def test_qr_carries_a_signed_token(self, ingresso: dict) -> None:
        conteudo = decode_token(ingresso["qr_token"], TOKEN_TYPE_TICKET)

        assert conteudo is not None
        assert conteudo["jti"] == ingresso["jti"]
        assert conteudo["evt"]

    def test_qr_does_not_expose_the_sequential_id(self, ingresso: dict) -> None:
        """O id revelaria volume de vendas e permitiria adivinhar vizinhos."""
        conteudo = decode_token(ingresso["qr_token"], TOKEN_TYPE_TICKET)
        assert str(ingresso["id"]) != conteudo["jti"]

    def test_token_signed_with_another_key_is_invalid(
        self, ingresso: dict
    ) -> None:
        forjado = jwt.encode(
            {"jti": ingresso["jti"], "evt": 1, "type": TOKEN_TYPE_TICKET},
            "chave-errada", algorithm="HS256",
        )
        assert decode_token(forjado, TOKEN_TYPE_TICKET) is None

    def test_tampered_payload_is_invalid(self, ingresso: dict) -> None:
        cabecalho, corpo, assinatura = ingresso["qr_token"].split(".")
        adulterado = f"{cabecalho}.{corpo[:-4]}AAAA.{assinatura}"
        assert decode_token(adulterado, TOKEN_TYPE_TICKET) is None

    def test_ticket_token_is_not_a_session_credential(
        self, client: TestClient, ingresso: dict
    ) -> None:
        r = client.get("/auth/me",
                       headers={"Authorization": f"Bearer {ingresso['qr_token']}"})
        assert r.status_code == 401
