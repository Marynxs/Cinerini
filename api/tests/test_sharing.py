"""Compartilhamento de ingresso por link revogável."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Seat, ShareLink, Showing, Ticket, TicketStatus
from app.security import TOKEN_TYPE_TICKET, decode_token

PAGAMENTO = {"card_number": "4111111111111111", "holder_name": "Bruno Tavares"}


@pytest.fixture
def ticket_id(client: TestClient, auth, db: Session, showing: Showing) -> int:
    assento = db.scalars(
        select(Seat).where(Seat.showing_id == showing.id).limit(1)
    ).one()

    pedido = client.post(f"/showings/{showing.id}/reservations",
                         json={"seat_ids": [assento.id]},
                         headers=auth("customer")).json()
    resposta = client.post(f"/orders/{pedido['id']}/payment", json=PAGAMENTO,
                           headers=auth("customer")).json()
    return resposta["order"]["tickets"][0]["id"]


@pytest.fixture
def token(client: TestClient, auth, ticket_id: int) -> str:
    r = client.post(f"/tickets/{ticket_id}/share", headers=auth("customer"))
    assert r.status_code == 201
    return r.json()["token"]


class TestCreating:
    def test_owner_generates_a_link(
        self, client: TestClient, auth, ticket_id: int
    ) -> None:
        r = client.post(f"/tickets/{ticket_id}/share", headers=auth("customer"))
        assert r.status_code == 201
        assert r.json()["revoked"] is False

    def test_token_is_long_enough_to_resist_guessing(self, token: str) -> None:
        assert len(token) >= 40

    def test_two_links_for_the_same_ticket_differ(
        self, client: TestClient, auth, ticket_id: int
    ) -> None:
        """Vários links permitem revogar um sem derrubar os outros."""
        primeiro = client.post(f"/tickets/{ticket_id}/share",
                               headers=auth("customer")).json()["token"]
        segundo = client.post(f"/tickets/{ticket_id}/share",
                              headers=auth("customer")).json()["token"]
        assert primeiro != segundo

    def test_another_customer_cannot_share_my_ticket(
        self, client: TestClient, auth, ticket_id: int
    ) -> None:
        r = client.post(f"/tickets/{ticket_id}/share", headers=auth("customer2"))
        assert r.status_code == 404

    def test_cancelled_ticket_cannot_be_shared(
        self, client: TestClient, auth, db: Session, ticket_id: int
    ) -> None:
        ingresso = db.get(Ticket, ticket_id)
        ingresso.status = TicketStatus.CANCELLED
        db.commit()

        r = client.post(f"/tickets/{ticket_id}/share", headers=auth("customer"))
        assert r.status_code == 409


class TestOpening:
    def test_anyone_with_the_link_sees_the_ticket(
        self, client: TestClient, token: str
    ) -> None:
        """Sem token de sessão: o link é a credencial."""
        r = client.get(f"/share/{token}")
        assert r.status_code == 200
        assert r.json()["seat_label"]

    def test_shows_what_the_screen_needs(
        self, client: TestClient, token: str
    ) -> None:
        corpo = client.get(f"/share/{token}").json()
        for campo in ("event_title", "venue_name", "room_name", "starts_at",
                      "seat_label", "qr_token"):
            assert corpo[campo], f"{campo} veio vazio"

    def test_does_not_expose_the_buyer(
        self, client: TestClient, token: str
    ) -> None:
        """O link circula por mensagem e pode chegar além do pretendido."""
        corpo = client.get(f"/share/{token}").json()
        assert "customer" not in corpo
        assert "Bruno" not in str(corpo)

    def test_qr_works_from_the_shared_view(
        self, client: TestClient, token: str
    ) -> None:
        """Quem recebe o link precisa conseguir entrar com ele."""
        corpo = client.get(f"/share/{token}").json()
        conteudo = decode_token(corpo["qr_token"], TOKEN_TYPE_TICKET)
        assert conteudo is not None

    def test_unknown_token_is_not_found(self, client: TestClient) -> None:
        assert client.get("/share/inventado").status_code == 404


class TestRevoking:
    def test_owner_revokes(
        self, client: TestClient, auth, token: str
    ) -> None:
        assert client.delete(f"/share/{token}",
                             headers=auth("customer")).status_code == 204

    def test_revoked_link_stops_working(
        self, client: TestClient, auth, token: str
    ) -> None:
        client.delete(f"/share/{token}", headers=auth("customer"))

        r = client.get(f"/share/{token}")
        assert r.status_code == 410
        assert "desativado" in r.json()["detail"]

    def test_revoking_does_not_invalidate_the_ticket(
        self, client: TestClient, auth, db: Session, token: str, ticket_id: int
    ) -> None:
        """É a razão de o token do link ser separado da assinatura do QR."""
        client.delete(f"/share/{token}", headers=auth("customer"))

        assert db.get(Ticket, ticket_id).status == TicketStatus.VALID
        assert client.get("/me/tickets",
                          headers=auth("customer")).json()[0]["status"] == "valid"

    def test_revoking_one_link_keeps_the_others(
        self, client: TestClient, auth, ticket_id: int
    ) -> None:
        primeiro = client.post(f"/tickets/{ticket_id}/share",
                               headers=auth("customer")).json()["token"]
        segundo = client.post(f"/tickets/{ticket_id}/share",
                              headers=auth("customer")).json()["token"]

        client.delete(f"/share/{primeiro}", headers=auth("customer"))

        assert client.get(f"/share/{primeiro}").status_code == 410
        assert client.get(f"/share/{segundo}").status_code == 200

    def test_another_customer_cannot_revoke(
        self, client: TestClient, auth, token: str
    ) -> None:
        assert client.delete(f"/share/{token}",
                             headers=auth("customer2")).status_code == 404

    def test_revoked_link_is_kept_not_deleted(
        self, client: TestClient, auth, db: Session, token: str
    ) -> None:
        """Apagado devolveria 'não encontrado', indistinguível de URL errada."""
        client.delete(f"/share/{token}", headers=auth("customer"))

        link = db.scalar(select(ShareLink).where(ShareLink.token == token))
        assert link is not None
        assert link.revoked is True
