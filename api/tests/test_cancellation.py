"""Cancelamento de sessão e de ingresso (D10)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Order, OrderStatus, Seat, Showing, Ticket, TicketStatus

PAGAMENTO = {"card_number": "4111111111111111", "holder_name": "Bruno Tavares"}
MOTIVO = {"reason": "Problema no projetor"}


@pytest.fixture
def seats(db: Session, showing: Showing) -> list[Seat]:
    return list(db.scalars(
        select(Seat).where(Seat.showing_id == showing.id)
        .order_by(Seat.row_label, Seat.number)
    ))


def _comprar(client: TestClient, auth, showing: Showing, ids: list[int],
             papel: str = "customer") -> dict:
    pedido = client.post(f"/showings/{showing.id}/reservations",
                         json={"seat_ids": ids}, headers=auth(papel)).json()
    resposta = client.post(f"/orders/{pedido['id']}/payment", json=PAGAMENTO,
                           headers=auth(papel)).json()
    return resposta["order"]


class TestCancelShowing:
    def test_organizer_cancels_with_reason(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        r = client.post(f"/showings/{showing.id}/cancel", json=MOTIVO,
                        headers=auth("organizer"))

        assert r.status_code == 200
        assert r.json()["cancelled_at"]
        assert r.json()["cancellation_reason"] == "Problema no projetor"

    def test_reason_is_required(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        """Cancelar sem dizer por quê informa que algo houve e esconde o quê."""
        r = client.post(f"/showings/{showing.id}/cancel", json={"reason": ""},
                        headers=auth("organizer"))
        assert r.status_code == 422

    def test_tickets_are_cancelled(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        pedido = _comprar(client, auth, showing, [seats[0].id, seats[1].id])
        client.post(f"/showings/{showing.id}/cancel", json=MOTIVO,
                    headers=auth("organizer"))

        ingressos = db.scalars(
            select(Ticket).where(Ticket.order_id == pedido["id"])
        ).all()
        assert all(t.status == TicketStatus.CANCELLED for t in ingressos)

    def test_order_records_the_refund(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        pedido = _comprar(client, auth, showing, [seats[0].id])
        client.post(f"/showings/{showing.id}/cancel", json=MOTIVO,
                    headers=auth("organizer"))

        assert db.get(Order, pedido["id"]).status == OrderStatus.CANCELLED

    def test_seats_return_to_stock(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        """Não exige código: o índice parcial solta a poltrona sozinho."""
        _comprar(client, auth, showing, [seats[0].id])
        client.post(f"/showings/{showing.id}/cancel", json=MOTIVO,
                    headers=auth("organizer"))

        mapa = client.get(f"/showings/{showing.id}/seats").json()
        assert not any(a["taken"] for a in mapa)

    def test_cancelled_showing_leaves_the_catalog(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        client.post(f"/showings/{showing.id}/cancel", json=MOTIVO,
                    headers=auth("organizer"))

        sessoes = [s for f in client.get("/events").json()
                   for s in f["showings"]]
        assert showing.id not in [s["id"] for s in sessoes]

    def test_holder_sees_the_reason(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        """A explicação precisa estar onde a pessoa procuraria o ingresso."""
        _comprar(client, auth, showing, [seats[0].id])
        client.post(f"/showings/{showing.id}/cancel", json=MOTIVO,
                    headers=auth("organizer"))

        ingressos = client.get("/me/tickets", headers=auth("customer")).json()
        assert len(ingressos) == 1
        assert ingressos[0]["showing_cancelled"] is True
        assert ingressos[0]["cancellation_reason"] == "Problema no projetor"

    def test_reason_survives_longer_than_a_self_cancel(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        """Prazo diferente: quem cancelou já sabe, quem foi cancelado não.

        A explicação precisa continuar lá perto da data em que a pessoa iria,
        e não expirar numa janela de minutos como o cancelamento próprio.
        """
        pedido = _comprar(client, auth, showing, [seats[0].id])
        client.post(f"/showings/{showing.id}/cancel", json=MOTIVO,
                    headers=auth("organizer"))

        ingresso = db.get(Ticket, pedido["tickets"][0]["id"])
        ingresso.cancelled_at = datetime.now(timezone.utc) - timedelta(hours=6)
        db.commit()

        lista = client.get("/me/tickets", headers=auth("customer")).json()
        assert len(lista) == 1
        assert lista[0]["cancellation_reason"] == "Problema no projetor"

    def test_reason_leaves_once_the_showing_has_passed(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        _comprar(client, auth, showing, [seats[0].id])
        client.post(f"/showings/{showing.id}/cancel", json=MOTIVO,
                    headers=auth("organizer"))

        showing.starts_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

        assert client.get("/me/tickets", headers=auth("customer")).json() == []

    def test_cancelling_twice_is_refused(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        client.post(f"/showings/{showing.id}/cancel", json=MOTIVO,
                    headers=auth("organizer"))
        r = client.post(f"/showings/{showing.id}/cancel", json=MOTIVO,
                        headers=auth("organizer"))
        assert r.status_code == 409

    def test_another_organizer_cannot_cancel(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        r = client.post(f"/showings/{showing.id}/cancel", json=MOTIVO,
                        headers=auth("organizer2"))
        assert r.status_code == 404

    def test_used_ticket_is_not_reverted(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        """Quem já entrou entrou; apagar isso falsificaria o histórico."""
        pedido = _comprar(client, auth, showing, [seats[0].id])
        ingresso = db.get(Ticket, pedido["tickets"][0]["id"])
        ingresso.status = TicketStatus.USED
        db.commit()

        client.post(f"/showings/{showing.id}/cancel", json=MOTIVO,
                    headers=auth("organizer"))

        db.refresh(ingresso)
        assert ingresso.status == TicketStatus.USED


class TestCancelTicket:
    def test_customer_cancels_own_ticket(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        pedido = _comprar(client, auth, showing, [seats[0].id])
        ticket_id = pedido["tickets"][0]["id"]

        r = client.post(f"/tickets/{ticket_id}/cancel", headers=auth("customer"))
        assert r.status_code == 200
        assert r.json()[0]["status"] == "cancelled"

    def test_seat_returns_to_stock(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        pedido = _comprar(client, auth, showing, [seats[0].id])
        client.post(f"/tickets/{pedido['tickets'][0]['id']}/cancel",
                    headers=auth("customer"))

        outro = client.post(f"/showings/{showing.id}/reservations",
                            json={"seat_ids": [seats[0].id]},
                            headers=auth("customer2"))
        assert outro.status_code == 201

    def test_partial_cancel_keeps_the_order_alive(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        """Compra de duas com uma devolvida continua sendo uma compra."""
        pedido = _comprar(client, auth, showing, [seats[0].id, seats[1].id])
        client.post(f"/tickets/{pedido['tickets'][0]['id']}/cancel",
                    headers=auth("customer"))

        assert db.get(Order, pedido["id"]).status == OrderStatus.PAID

    def test_cancelling_all_closes_the_order(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        pedido = _comprar(client, auth, showing, [seats[0].id, seats[1].id])
        for t in pedido["tickets"]:
            client.post(f"/tickets/{t['id']}/cancel", headers=auth("customer"))

        assert db.get(Order, pedido["id"]).status == OrderStatus.CANCELLED

    def test_another_customer_cannot_cancel(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        pedido = _comprar(client, auth, showing, [seats[0].id])
        r = client.post(f"/tickets/{pedido['tickets'][0]['id']}/cancel",
                        headers=auth("customer2"))
        assert r.status_code == 404

    def test_used_ticket_cannot_be_cancelled(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        pedido = _comprar(client, auth, showing, [seats[0].id])
        ingresso = db.get(Ticket, pedido["tickets"][0]["id"])
        ingresso.status = TicketStatus.USED
        db.commit()

        r = client.post(f"/tickets/{ingresso.id}/cancel", headers=auth("customer"))
        assert r.status_code == 409

    def test_cancelled_ticket_lingers_briefly(
        self, client: TestClient, auth, showing: Showing, seats: list[Seat]
    ) -> None:
        """Sumir no mesmo instante do clique pareceria erro, não confirmação."""
        pedido = _comprar(client, auth, showing, [seats[0].id])
        client.post(f"/tickets/{pedido['tickets'][0]['id']}/cancel",
                    headers=auth("customer"))

        lista = client.get("/me/tickets", headers=auth("customer")).json()
        assert [t["status"] for t in lista] == ["cancelled"]

    def test_cancelled_ticket_leaves_the_list_after_the_window(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        pedido = _comprar(client, auth, showing, [seats[0].id])
        ingresso = db.get(Ticket, pedido["tickets"][0]["id"])
        client.post(f"/tickets/{ingresso.id}/cancel", headers=auth("customer"))

        db.refresh(ingresso)
        ingresso.cancelled_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        assert client.get("/me/tickets", headers=auth("customer")).json() == []

    def test_the_ticket_row_is_never_deleted(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        """Some da lista, não do banco: é registro de uma compra que houve."""
        pedido = _comprar(client, auth, showing, [seats[0].id])
        ingresso_id = pedido["tickets"][0]["id"]
        client.post(f"/tickets/{ingresso_id}/cancel", headers=auth("customer"))

        ingresso = db.get(Ticket, ingresso_id)
        ingresso.cancelled_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        client.get("/me/tickets", headers=auth("customer"))
        assert db.get(Ticket, ingresso_id) is not None

    def test_cannot_cancel_after_the_showing_started(
        self, client: TestClient, auth, db: Session, showing: Showing,
        seats: list[Seat],
    ) -> None:
        """Devolver o assento depois do início venderia um lugar inútil."""
        pedido = _comprar(client, auth, showing, [seats[0].id])

        showing.starts_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.commit()

        r = client.post(f"/tickets/{pedido['tickets'][0]['id']}/cancel",
                        headers=auth("customer"))
        assert r.status_code == 409
