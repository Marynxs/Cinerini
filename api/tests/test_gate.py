"""Validação na portaria: os seis desfechos, a corrida entre duas leituras,
e o cadastro da portaria pelo organizador.

Duas das quatro garantias do projeto se resolvem aqui — o ingresso que não
pode ser validado duas vezes, e o ingresso legítimo de outro lugar que não
pode virar "inválido".
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Event, EventStatus, Role, Room, Seat, Showing, Ticket, TicketStatus, User,
)
from app.seating import generate_seats
from app.security import ALGORITHM, TOKEN_TYPE_TICKET, create_ticket_token

PAGAMENTO = {"card_number": "4111111111111111", "holder_name": "Bruno Tavares"}
SENHA_NOVA = "senhaDaPortaria1"


@pytest.fixture
def gate_bound(db: Session, users: dict[str, User], showing: Showing) -> User:
    """A portaria só existe vinculada a uma sessão."""
    users["gate"].gate_showing_id = showing.id
    db.commit()
    return users["gate"]


def _comprar(client: TestClient, auth, db: Session, sessao: Showing) -> Ticket:
    assento = db.scalars(
        select(Seat).where(Seat.showing_id == sessao.id).limit(1)
    ).one()

    pedido = client.post(f"/showings/{sessao.id}/reservations",
                         json={"seat_ids": [assento.id]},
                         headers=auth("customer")).json()
    resposta = client.post(f"/orders/{pedido['id']}/payment", json=PAGAMENTO,
                           headers=auth("customer")).json()

    return db.get(Ticket, resposta["order"]["tickets"][0]["id"])


def _sessao(db: Session, evento_id: int, sala: Room, dias: int) -> Showing:
    s = Showing(event_id=evento_id, room_id=sala.id, price_cents=2900,
                starts_at=datetime.now(timezone.utc) + timedelta(days=dias))
    db.add(s)
    db.flush()
    generate_seats(db, s)
    db.commit()
    return s


@pytest.fixture
def ticket(client: TestClient, auth, db: Session, showing: Showing) -> Ticket:
    return _comprar(client, auth, db, showing)


@pytest.fixture
def qr(ticket: Ticket, showing: Showing) -> str:
    return create_ticket_token(ticket.jti, showing.id)


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

    def test_shows_the_session_it_belongs_to(
        self, client: TestClient, auth, gate_bound: User, qr: str
    ) -> None:
        """Horário, cinema e sala: é o que se confere com a pessoa na frente."""
        sessao = validar(client, auth, qr)["showing"]

        assert sessao["event_title"] == "Filme de Teste"
        assert sessao["venue_name"] == "Cine Teste"
        assert sessao["venue_city"] == "São Paulo"
        assert sessao["room_name"] == "Sala 1"
        assert sessao["starts_at"]

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
        """Digitação manual é o caminho de quando a câmera falha (D16)."""
        assert validar(client, auth, ticket.jti)["result"] == "valid"

    def test_printed_code_is_case_insensitive(
        self, client: TestClient, auth, gate_bound: User, ticket: Ticket
    ) -> None:
        """Ninguém digita um uuid respeitando a caixa das letras."""
        assert validar(client, auth, ticket.jti.upper())["result"] == "valid"


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
            {"jti": ticket.jti, "shw": showing.id, "type": TOKEN_TYPE_TICKET},
            "chave-que-nao-e-a-do-servidor",
            algorithm=ALGORITHM,
        )
        assert validar(client, auth, forjado)["result"] == "invalid"

    def test_unknown_but_well_formed_code_is_refused(
        self, client: TestClient, auth, gate_bound: User
    ) -> None:
        codigo = "00000000-0000-4000-8000-000000000000"
        assert validar(client, auth, codigo)["result"] == "invalid"

    def test_signature_pointing_to_another_showing_is_refused(
        self, client: TestClient, auth, db: Session, gate_bound: User,
        showing: Showing, room: Room, ticket: Ticket
    ) -> None:
        """Token assinado por nós, montado para apontar outra exibição.

        Não é "outra sessão": a exibição que a assinatura afirma não é a do
        ingresso, então o token não corresponde a nada real.
        """
        outra = _sessao(db, showing.event_id, room, dias=3)
        assert validar(client, auth,
                       create_ticket_token(ticket.jti, outra.id))["result"] == "invalid"

    def test_access_token_is_not_accepted_as_a_ticket(
        self, client: TestClient, auth, gate_bound: User
    ) -> None:
        """O mesmo segredo assina os dois; o campo `type` os separa."""
        credencial = auth("customer")["Authorization"].removeprefix("Bearer ")
        assert validar(client, auth, credencial)["result"] == "invalid"


class TestWrongShowing:
    """Mesmo filme, exibição diferente — outro horário, sala ou cinema."""

    @pytest.fixture
    def qr_de_outra_sessao(
        self, client: TestClient, auth, db: Session, gate_bound: User,
        showing: Showing, room: Room
    ) -> str:
        outra = _sessao(db, showing.event_id, room, dias=2)
        t = _comprar(client, auth, db, outra)
        return create_ticket_token(t.jti, outra.id)

    def test_has_its_own_state(
        self, client: TestClient, auth, qr_de_outra_sessao: str
    ) -> None:
        """O buraco que o vínculo por evento deixava aberto (D21)."""
        corpo = validar(client, auth, qr_de_outra_sessao)
        assert corpo["result"] == "wrong_showing"

    def test_names_the_right_session(
        self, client: TestClient, auth, qr_de_outra_sessao: str
    ) -> None:
        """Quem veio na hora errada precisa saber qual é a certa."""
        corpo = validar(client, auth, qr_de_outra_sessao)
        assert corpo["showing"]["event_title"] == "Filme de Teste"
        assert corpo["showing"]["starts_at"]

    def test_does_not_consume_the_ticket(
        self, client: TestClient, auth, db: Session, qr_de_outra_sessao: str
    ) -> None:
        """A sessão certa ainda precisa aceitá-lo depois."""
        validar(client, auth, qr_de_outra_sessao)

        jti = jwt.decode(qr_de_outra_sessao, get_settings().secret_key,
                         algorithms=[ALGORITHM])["jti"]
        t = db.scalars(select(Ticket).where(Ticket.jti == jti)).one()

        assert t.status == TicketStatus.VALID
        assert t.used_at is None

    def test_typed_code_is_also_distinguished(
        self, client: TestClient, auth, db: Session, qr_de_outra_sessao: str
    ) -> None:
        """Sem assinatura, a exibição vem do banco — mesmo veredito."""
        jti = jwt.decode(qr_de_outra_sessao, get_settings().secret_key,
                         algorithms=[ALGORITHM])["jti"]
        assert validar(client, auth, jti)["result"] == "wrong_showing"


class TestWrongEvent:
    """Filme diferente. Estado separado de "outra sessão" porque a reação de
    quem opera é outra: um manda para outro horário, o outro para outra sala.
    """

    @pytest.fixture
    def qr_de_outro_evento(
        self, client: TestClient, auth, db: Session, users: dict[str, User],
        room: Room, gate_bound: User
    ) -> str:
        evento = Event(organizer_id=users["organizer"].id, title="Outro Filme",
                       status=EventStatus.PUBLISHED)
        db.add(evento)
        db.flush()

        outra = _sessao(db, evento.id, room, dias=2)
        t = _comprar(client, auth, db, outra)
        return create_ticket_token(t.jti, outra.id)

    def test_has_its_own_state(
        self, client: TestClient, auth, qr_de_outro_evento: str
    ) -> None:
        """Garantia 4: não pode colapsar em "inválido"."""
        assert validar(client, auth, qr_de_outro_evento)["result"] == "wrong_event"

    def test_names_the_right_event(
        self, client: TestClient, auth, qr_de_outro_evento: str
    ) -> None:
        corpo = validar(client, auth, qr_de_outro_evento)
        assert corpo["showing"]["event_title"] == "Outro Filme"

    def test_does_not_consume_the_ticket(
        self, client: TestClient, auth, db: Session, qr_de_outro_evento: str
    ) -> None:
        validar(client, auth, qr_de_outro_evento)

        jti = jwt.decode(qr_de_outro_evento, get_settings().secret_key,
                         algorithms=[ALGORITHM])["jti"]
        t = db.scalars(select(Ticket).where(Ticket.jti == jti)).one()

        assert t.status == TicketStatus.VALID


class TestCancelled:
    def test_refunded_ticket_is_not_called_invalid(
        self, client: TestClient, auth, gate_bound: User, ticket: Ticket, qr: str
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

    def test_anonymous_cannot_validate(
        self, client: TestClient, gate_bound: User, qr: str
    ) -> None:
        assert client.post("/gate/validations", json={"code": qr}).status_code == 401

    def test_unbound_gate_is_a_configuration_error(
        self, client: TestClient, auth, users: dict[str, User], qr: str
    ) -> None:
        """Sem vínculo, tudo seria recusa — e isso é erro de cadastro."""
        assert users["gate"].gate_showing_id is None

        r = client.post("/gate/validations", json={"code": qr},
                        headers=auth("gate"))
        assert r.status_code == 409

    def test_gate_reports_the_session_it_serves(
        self, client: TestClient, auth, gate_bound: User
    ) -> None:
        r = client.get("/gate/me", headers=auth("gate"))
        assert r.status_code == 200
        assert r.json()["showing"]["event_title"] == "Filme de Teste"
        assert r.json()["showing"]["room_name"] == "Sala 1"


class TestCreatingGates:
    """Portaria não se auto-cadastra: quem a cria é o organizador do evento."""

    DADOS = {"name": "Porta A", "email": "porta.a@cinerini.com.br",
             "password": SENHA_NOVA}

    def test_organizer_creates_a_gate_for_a_session(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        r = client.post(f"/showings/{showing.id}/gates", json=self.DADOS,
                        headers=auth("organizer"))
        assert r.status_code == 201, r.text
        assert r.json()["showing"]["event_title"] == "Filme de Teste"

    def test_the_new_gate_can_log_in_and_validate(
        self, client: TestClient, auth, db: Session, showing: Showing,
        qr: str
    ) -> None:
        """Nasce pronta para trabalhar, sem passo extra de vinculação."""
        client.post(f"/showings/{showing.id}/gates", json=self.DADOS,
                    headers=auth("organizer"))

        entrada = client.post("/auth/login", json={
            "email": self.DADOS["email"], "password": SENHA_NOVA})
        assert entrada.status_code == 200

        cabecalho = {"Authorization": f"Bearer {entrada.json()['access_token']}"}
        r = client.post("/gate/validations", json={"code": qr}, headers=cabecalho)

        assert r.status_code == 200
        assert r.json()["result"] == "valid"

    def test_public_signup_never_creates_a_gate(
        self, client: TestClient
    ) -> None:
        """O papel não pode vir do formulário: decide quem entra na sala."""
        r = client.post("/auth/register", json={
            "name": "Espertinho", "email": "esperto@cinerini.com.br",
            "password": SENHA_NOVA, "role": "gate"})

        assert r.status_code == 201
        assert r.json()["user"]["role"] == "customer"

    def test_customer_cannot_create_a_gate(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        r = client.post(f"/showings/{showing.id}/gates", json=self.DADOS,
                        headers=auth("customer"))
        assert r.status_code == 403

    def test_another_organizer_cannot_create_a_gate_here(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        """Montar portaria na sessão alheia é decidir quem entra nela."""
        r = client.post(f"/showings/{showing.id}/gates", json=self.DADOS,
                        headers=auth("organizer2"))
        assert r.status_code == 404

    def test_duplicate_email_is_refused(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        client.post(f"/showings/{showing.id}/gates", json=self.DADOS,
                    headers=auth("organizer"))
        r = client.post(f"/showings/{showing.id}/gates", json=self.DADOS,
                        headers=auth("organizer"))
        assert r.status_code == 409


class TestRebinding:
    """A mesma porta atende sessões diferentes ao longo do dia."""

    def test_organizer_points_the_gate_at_another_session(
        self, client: TestClient, auth, db: Session, gate_bound: User,
        showing: Showing, room: Room
    ) -> None:
        outra = _sessao(db, showing.event_id, room, dias=4)

        r = client.patch(f"/gates/{gate_bound.id}",
                         json={"showing_id": outra.id},
                         headers=auth("organizer"))

        assert r.status_code == 200
        assert r.json()["showing_id"] == outra.id

    def test_rebinding_changes_what_is_accepted(
        self, client: TestClient, auth, db: Session, gate_bound: User,
        showing: Showing, room: Room, qr: str
    ) -> None:
        """O ingresso de antes passa a ser de outra sessão, não inválido."""
        outra = _sessao(db, showing.event_id, room, dias=4)
        client.patch(f"/gates/{gate_bound.id}", json={"showing_id": outra.id},
                     headers=auth("organizer"))

        assert validar(client, auth, qr)["result"] == "wrong_showing"

    def test_unbinding_stops_validation(
        self, client: TestClient, auth, gate_bound: User, qr: str
    ) -> None:
        """Entre uma sessão e a seguinte, a porta não deve aceitar nada."""
        client.patch(f"/gates/{gate_bound.id}", json={"showing_id": None},
                     headers=auth("organizer"))

        r = client.post("/gate/validations", json={"code": qr},
                        headers=auth("gate"))
        assert r.status_code == 409

    def test_another_organizer_cannot_rebind(
        self, client: TestClient, auth, gate_bound: User
    ) -> None:
        r = client.patch(f"/gates/{gate_bound.id}", json={"showing_id": None},
                         headers=auth("organizer2"))
        assert r.status_code == 404

    def test_gate_cannot_rebind_itself(
        self, client: TestClient, auth, gate_bound: User
    ) -> None:
        """Escolher a própria sessão é escolher quais ingressos aceitar."""
        r = client.patch(f"/gates/{gate_bound.id}", json={"showing_id": None},
                         headers=auth("gate"))
        assert r.status_code == 403


class TestListingGates:
    def test_organizer_sees_gates_of_their_sessions(
        self, client: TestClient, auth, gate_bound: User
    ) -> None:
        r = client.get("/gates", headers=auth("organizer"))
        assert r.status_code == 200
        assert gate_bound.id in [g["id"] for g in r.json()]

    def test_gates_of_other_organizers_are_hidden(
        self, client: TestClient, auth, gate_bound: User
    ) -> None:
        r = client.get("/gates", headers=auth("organizer2"))
        assert gate_bound.id not in [g["id"] for g in r.json()]

    def test_unbound_gates_are_listed(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        """São elas que precisam de atenção antes da próxima sessão."""
        assert users["gate"].gate_showing_id is None

        r = client.get("/gates", headers=auth("organizer"))
        assert users["gate"].id in [g["id"] for g in r.json()]
