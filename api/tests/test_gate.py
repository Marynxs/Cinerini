"""Validação na portaria: os cinco desfechos e a corrida entre duas leituras.

Duas das quatro garantias do projeto se resolvem aqui — o ingresso que não
pode ser validado duas vezes, e o evento errado que não pode virar
"inválido".
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Event, EventStatus, Room, Seat, Showing, Ticket, TicketStatus, User,
)
from app.seating import generate_seats
from app.security import ALGORITHM, TOKEN_TYPE_TICKET, create_ticket_token

PAGAMENTO = {"card_number": "4111111111111111", "holder_name": "Bruno Tavares"}


@pytest.fixture
def gate_bound(db: Session, users: dict[str, User], showing: Showing) -> User:
    """A portaria só existe vinculada a um evento."""
    users["gate"].gate_event_id = showing.event_id
    db.commit()
    return users["gate"]


@pytest.fixture
def ticket(client: TestClient, auth, db: Session, showing: Showing) -> Ticket:
    assento = db.scalars(
        select(Seat).where(Seat.showing_id == showing.id).limit(1)
    ).one()

    pedido = client.post(f"/showings/{showing.id}/reservations",
                         json={"seat_ids": [assento.id]},
                         headers=auth("customer")).json()
    resposta = client.post(f"/orders/{pedido['id']}/payment", json=PAGAMENTO,
                           headers=auth("customer")).json()

    return db.get(Ticket, resposta["order"]["tickets"][0]["id"])


@pytest.fixture
def qr(ticket: Ticket, showing: Showing) -> str:
    return create_ticket_token(ticket.jti, showing.event_id)


def validar(client: TestClient, auth, codigo: str):
    r = client.post("/gate/validations", json={"code": codigo},
                    headers=auth("gate"))
    assert r.status_code == 200, r.text
    return r.json()


class TestValid:
    def test_signed_qr_is_accepted(
        self, client: TestClient, auth, gate_bound: User, qr: str
    ) -> None:
        assert validar(client, auth, qr)["result"] == "valid"

    def test_shows_seat_and_customer(
        self, client: TestClient, auth, gate_bound: User, qr: str
    ) -> None:
        """Sem poltrona e nome, o operador não tem como conferir a pessoa."""
        corpo = validar(client, auth, qr)
        assert corpo["seat_label"] == "A1"
        assert corpo["customer_name"] == "Cliente"

    def test_marks_the_ticket_as_used(
        self, client: TestClient, auth, db: Session, gate_bound: User,
        ticket: Ticket, qr: str
    ) -> None:
        validar(client, auth, qr)
        db.refresh(ticket)

        assert ticket.status == TicketStatus.USED
        assert ticket.used_at is not None
        assert ticket.validated_by == gate_bound.id

    def test_printed_code_also_works(
        self, client: TestClient, auth, gate_bound: User, ticket: Ticket
    ) -> None:
        """Digitação manual é o caminho de quando a câmera falha (D17)."""
        assert validar(client, auth, ticket.jti)["result"] == "valid"

    def test_printed_code_is_case_insensitive(
        self, client: TestClient, auth, gate_bound: User, ticket: Ticket
    ) -> None:
        """Ninguém digita um uuid respeitando a caixa das letras."""
        corpo = validar(client, auth, ticket.jti.upper())
        assert corpo["result"] == "valid"


class TestAlreadyUsed:
    def test_second_read_is_refused(
        self, client: TestClient, auth, gate_bound: User, qr: str
    ) -> None:
        assert validar(client, auth, qr)["result"] == "valid"
        assert validar(client, auth, qr)["result"] == "already_used"

    def test_shows_the_previous_time(
        self, client: TestClient, auth, gate_bound: User, qr: str
    ) -> None:
        """Sem o horário anterior não dá para saber se foi agora ou ontem."""
        validar(client, auth, qr)
        assert validar(client, auth, qr)["used_at"] is not None

    def test_the_first_validator_is_kept(
        self, client: TestClient, auth, db: Session, gate_bound: User,
        ticket: Ticket, qr: str
    ) -> None:
        """A segunda leitura não pode sobrescrever quem validou de fato."""
        validar(client, auth, qr)
        db.refresh(ticket)
        primeiro = ticket.used_at

        validar(client, auth, qr)
        db.refresh(ticket)

        assert ticket.used_at == primeiro


class TestInvalid:
    def test_garbage_is_refused(
        self, client: TestClient, auth, gate_bound: User
    ) -> None:
        assert validar(client, auth, "isto-nao-e-codigo")["result"] == "invalid"

    def test_tampered_signature_is_refused(
        self, client: TestClient, auth, gate_bound: User, ticket: Ticket,
        showing: Showing
    ) -> None:
        """Garantia 2: sem a chave do servidor não se produz código aceito."""
        forjado = jwt.encode(
            {"jti": ticket.jti, "evt": showing.event_id,
             "type": TOKEN_TYPE_TICKET},
            "chave-que-nao-e-a-do-servidor",
            algorithm=ALGORITHM,
        )
        assert validar(client, auth, forjado)["result"] == "invalid"

    def test_unknown_but_well_formed_code_is_refused(
        self, client: TestClient, auth, gate_bound: User
    ) -> None:
        codigo = "00000000-0000-4000-8000-000000000000"
        assert validar(client, auth, codigo)["result"] == "invalid"

    def test_signature_pointing_to_the_wrong_event_is_refused(
        self, client: TestClient, auth, db: Session, gate_bound: User,
        users: dict[str, User], ticket: Ticket
    ) -> None:
        """Token assinado por nós, mas montado para apontar outro evento.

        Não é "outro evento": o evento que a assinatura afirma não é o do
        ingresso, então o token não corresponde a nada real.
        """
        outro = Event(organizer_id=users["organizer"].id, title="Outro",
                      status=EventStatus.PUBLISHED)
        db.add(outro)
        db.commit()

        adulterado = create_ticket_token(ticket.jti, outro.id)
        assert validar(client, auth, adulterado)["result"] == "invalid"

    def test_access_token_is_not_accepted_as_a_ticket(
        self, client: TestClient, auth, gate_bound: User
    ) -> None:
        """O mesmo segredo assina os dois; o campo `type` os separa."""
        credencial = auth("customer")["Authorization"].removeprefix("Bearer ")
        assert validar(client, auth, credencial)["result"] == "invalid"


class TestWrongEvent:
    @pytest.fixture
    def outro_evento(
        self, db: Session, users: dict[str, User], room: Room, gate_bound: User
    ) -> Showing:
        """Sessão de um evento ao qual esta portaria não atende."""
        evento = Event(organizer_id=users["organizer"].id, title="Outro Filme",
                       status=EventStatus.PUBLISHED)
        db.add(evento)
        db.flush()

        s = Showing(event_id=evento.id, room_id=room.id, price_cents=2500,
                    starts_at=datetime.now(timezone.utc) + timedelta(days=2))
        db.add(s)
        db.flush()
        generate_seats(db, s)
        db.commit()
        return s

    @pytest.fixture
    def qr_de_outro(
        self, client: TestClient, auth, db: Session, outro_evento: Showing
    ) -> str:
        assento = db.scalars(
            select(Seat).where(Seat.showing_id == outro_evento.id).limit(1)
        ).one()

        pedido = client.post(f"/showings/{outro_evento.id}/reservations",
                             json={"seat_ids": [assento.id]},
                             headers=auth("customer")).json()
        r = client.post(f"/orders/{pedido['id']}/payment", json=PAGAMENTO,
                        headers=auth("customer")).json()

        t = db.get(Ticket, r["order"]["tickets"][0]["id"])
        return create_ticket_token(t.jti, outro_evento.event_id)

    def test_has_its_own_state(
        self, client: TestClient, auth, qr_de_outro: str
    ) -> None:
        """Garantia 4: não pode colapsar em "inválido"."""
        assert validar(client, auth, qr_de_outro)["result"] == "wrong_event"

    def test_names_the_right_event(
        self, client: TestClient, auth, qr_de_outro: str
    ) -> None:
        """Quem errou a porta precisa saber para qual ir."""
        corpo = validar(client, auth, qr_de_outro)
        assert corpo["ticket_event_title"] == "Outro Filme"

    def test_does_not_consume_the_ticket(
        self, client: TestClient, auth, db: Session, qr_de_outro: str
    ) -> None:
        """A portaria certa ainda precisa conseguir validá-lo depois."""
        validar(client, auth, qr_de_outro)

        jti = jwt.decode(qr_de_outro, get_settings().secret_key,
                         algorithms=[ALGORITHM])["jti"]
        t = db.scalars(select(Ticket).where(Ticket.jti == jti)).one()

        assert t.status == TicketStatus.VALID
        assert t.used_at is None

    def test_typed_code_of_another_event_is_also_distinguished(
        self, client: TestClient, auth, db: Session, qr_de_outro: str
    ) -> None:
        """Sem assinatura, o evento vem do banco — e o veredito é o mesmo."""
        jti = jwt.decode(qr_de_outro, get_settings().secret_key,
                         algorithms=[ALGORITHM])["jti"]
        assert validar(client, auth, jti)["result"] == "wrong_event"


class TestCancelled:
    def test_refunded_ticket_is_not_called_invalid(
        self, client: TestClient, auth, db: Session, gate_bound: User,
        ticket: Ticket, qr: str
    ) -> None:
        """Chamar de "inválido" trataria como fraudador quem só cancelou."""
        client.post(f"/tickets/{ticket.id}/cancel", headers=auth("customer"))

        assert validar(client, auth, qr)["result"] == "cancelled"

    def test_cancelled_ticket_is_not_consumed(
        self, client: TestClient, auth, db: Session, gate_bound: User,
        ticket: Ticket, qr: str
    ) -> None:
        client.post(f"/tickets/{ticket.id}/cancel", headers=auth("customer"))
        validar(client, auth, qr)
        db.refresh(ticket)

        assert ticket.status == TicketStatus.CANCELLED
        assert ticket.used_at is None


class TestAccess:
    def test_customer_cannot_validate(
        self, client: TestClient, auth, gate_bound: User, qr: str
    ) -> None:
        r = client.post("/gate/validations", json={"code": qr},
                        headers=auth("customer"))
        assert r.status_code == 403

    def test_organizer_cannot_validate(
        self, client: TestClient, auth, gate_bound: User, qr: str
    ) -> None:
        r = client.post("/gate/validations", json={"code": qr},
                        headers=auth("organizer"))
        assert r.status_code == 403

    def test_anonymous_cannot_validate(
        self, client: TestClient, gate_bound: User, qr: str
    ) -> None:
        r = client.post("/gate/validations", json={"code": qr})
        assert r.status_code == 401

    def test_unbound_gate_is_a_configuration_error(
        self, client: TestClient, auth, users: dict[str, User], qr: str
    ) -> None:
        """Sem vínculo, tudo seria "outro evento" — e isso é erro de cadastro."""
        assert users["gate"].gate_event_id is None

        r = client.post("/gate/validations", json={"code": qr},
                        headers=auth("gate"))
        assert r.status_code == 409

    def test_gate_reports_the_event_it_serves(
        self, client: TestClient, auth, gate_bound: User, showing: Showing
    ) -> None:
        r = client.get("/gate/me", headers=auth("gate"))
        assert r.status_code == 200
        assert r.json()["event_title"] == "Filme de Teste"
