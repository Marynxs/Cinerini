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
    Venue,
)
from app.seating import generate_seats
from app.security import ALGORITHM, TOKEN_TYPE_TICKET, create_ticket_token

PAGAMENTO = {"card_number": "4111111111111111", "holder_name": "Bruno Tavares"}
SENHA_NOVA = "senhaDaPortaria1"


@pytest.fixture
def gate_bound(db: Session, gate_hired: User, showing: Showing) -> User:
    """A mesma conta, já com o turno escolhido."""
    gate_hired.gate_showing_id = showing.id
    db.commit()
    return gate_hired


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


def _sessao(db: Session, evento_id: int, sala: Room, dias: int = 0,
            horas: int = 0) -> Showing:
    s = Showing(event_id=evento_id, room_id=sala.id, price_cents=2900,
                starts_at=datetime.now(timezone.utc)
                + timedelta(days=dias, hours=horas))
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
    """Portaria não se auto-cadastra: quem a cria é o organizador."""

    DADOS = {"name": "Porta A", "email": "porta.a@cinerini.com.br",
             "password": SENHA_NOVA}

    def test_organizer_creates_a_gate_for_a_venue(
        self, client: TestClient, auth, room: Room
    ) -> None:
        """A conta é da pessoa e do cinema, não da sessão (D24)."""
        r = client.post(f"/venues/{room.venue_id}/gates", json=self.DADOS,
                        headers=auth("organizer"))
        assert r.status_code == 201, r.text
        assert r.json()["venue_name"] == "Cine Teste"

    def test_the_new_gate_starts_without_a_shift(
        self, client: TestClient, auth, room: Room
    ) -> None:
        """Escolher o turno é o primeiro gesto de quem opera."""
        r = client.post(f"/venues/{room.venue_id}/gates", json=self.DADOS,
                        headers=auth("organizer"))
        assert r.json()["showing_id"] is None

    def test_the_new_gate_logs_in_picks_a_shift_and_validates(
        self, client: TestClient, auth, room: Room, showing: Showing, qr: str
    ) -> None:
        client.post(f"/venues/{room.venue_id}/gates", json=self.DADOS,
                    headers=auth("organizer"))

        entrada = client.post("/auth/login", json={
            "email": self.DADOS["email"], "password": SENHA_NOVA})
        assert entrada.status_code == 200
        cab = {"Authorization": f"Bearer {entrada.json()['access_token']}"}

        turnos = client.get("/gate/showings", headers=cab).json()
        assert showing.id in [s["showing_id"] for s in turnos]

        client.put("/gate/shift", json={"showing_id": showing.id}, headers=cab)
        r = client.post("/gate/validations", json={"code": qr}, headers=cab)

        assert r.status_code == 200
        assert r.json()["result"] == "valid"

    def test_public_signup_never_creates_a_gate(
        self, client: TestClient, users: dict[str, User]
    ) -> None:
        """O papel não pode vir do formulário: decide quem entra na sala."""
        r = client.post("/auth/register", json={
            "name": "Espertinho", "email": "esperto@cinerini.com.br",
            "password": SENHA_NOVA, "role": "gate"})

        assert r.status_code == 201
        assert r.json()["user"]["role"] == "customer"

    def test_customer_cannot_create_a_gate(
        self, client: TestClient, auth, room: Room
    ) -> None:
        r = client.post(f"/venues/{room.venue_id}/gates", json=self.DADOS,
                        headers=auth("customer"))
        assert r.status_code == 403

    def test_duplicate_email_is_refused(
        self, client: TestClient, auth, room: Room
    ) -> None:
        client.post(f"/venues/{room.venue_id}/gates", json=self.DADOS,
                    headers=auth("organizer"))
        r = client.post(f"/venues/{room.venue_id}/gates", json=self.DADOS,
                        headers=auth("organizer"))
        assert r.status_code == 409


class TestChoosingShift:
    """Quem escolhe a sessão do turno é quem trabalha (D24)."""

    def _cab(self, auth) -> dict[str, str]:
        return auth("gate")

    def test_lists_only_sessions_of_its_own_venue(
        self, client: TestClient, auth, db: Session, gate_hired: User,
        showing: Showing, users: dict[str, User]
    ) -> None:
        """O escopo vem da conta, não da escolha de quem opera."""
        outro = Venue(name="Cine Rival", city="Santos", city_ibge_id=3548500,
                      state="SP", address="Av. Ana Costa, 1")
        db.add(outro)
        db.flush()
        sala = Room(venue_id=outro.id, name="Sala X", rows=2, seats_per_row=2)
        db.add(sala)
        db.flush()
        alheia = _sessao(db, showing.event_id, sala, dias=1)

        ids = [s["showing_id"] for s in
               client.get("/gate/showings", headers=auth("gate")).json()]

        assert showing.id in ids
        assert alheia.id not in ids

    def test_choosing_a_shift_enables_validation(
        self, client: TestClient, auth, gate_hired: User, showing: Showing,
        qr: str
    ) -> None:
        antes = client.post("/gate/validations", json={"code": qr},
                            headers=auth("gate"))
        assert antes.status_code == 409

        client.put("/gate/shift", json={"showing_id": showing.id},
                   headers=auth("gate"))

        assert validar(client, auth, qr)["result"] == "valid"

    def test_changing_shift_changes_what_is_accepted(
        self, client: TestClient, auth, db: Session, gate_bound: User,
        showing: Showing, room: Room, qr: str
    ) -> None:
        """O ingresso de antes vira de outra sessão, não inválido."""
        outra = _sessao(db, showing.event_id, room, dias=1)
        r = client.put("/gate/shift", json={"showing_id": outra.id},
                       headers=auth("gate"))
        assert r.status_code == 200

        assert validar(client, auth, qr)["result"] == "wrong_showing"

    def test_ending_the_shift_stops_validation(
        self, client: TestClient, auth, gate_bound: User, qr: str
    ) -> None:
        """Entre uma sessão e a seguinte, a porta não deve aceitar nada."""
        client.put("/gate/shift", json={"showing_id": None},
                   headers=auth("gate"))

        r = client.post("/gate/validations", json={"code": qr},
                        headers=auth("gate"))
        assert r.status_code == 409

    def test_cannot_pick_a_session_of_another_venue(
        self, client: TestClient, auth, db: Session, gate_hired: User,
        showing: Showing
    ) -> None:
        """Mandar um id de fora não adianta: a lista é filtrada no servidor."""
        outro = Venue(name="Cine Alheio", city="Campinas",
                      city_ibge_id=3509502, state="SP", address="Rua A, 1")
        db.add(outro)
        db.flush()
        sala = Room(venue_id=outro.id, name="Sala Y", rows=2, seats_per_row=2)
        db.add(sala)
        db.flush()
        alheia = _sessao(db, showing.event_id, sala, dias=1)

        r = client.put("/gate/shift", json={"showing_id": alheia.id},
                       headers=auth("gate"))
        assert r.status_code == 404

    def test_gate_without_a_venue_cannot_list_shifts(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        """Cadastro pela metade é erro de configuração, não veredito."""
        assert users["gate"].gate_venue_id is None
        assert client.get("/gate/showings", headers=auth("gate")).status_code == 409

    def test_organizer_also_opens_the_gate(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        """Num cinema pequeno quem publica é quem fica na porta (D27).

        O escopo dele não é um cinema, e sim os eventos que publicou — não
        precisa de `gate_venue_id` para escolher turno.
        """
        r = client.put("/gate/shift", json={"showing_id": showing.id},
                       headers=auth("organizer"))
        assert r.status_code == 200
        assert r.json()["showing_id"] == showing.id

    def test_any_organizer_takes_any_session(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        """Não há "catálogo do outro": a operação é uma só (D29)."""
        r = client.put("/gate/shift", json={"showing_id": showing.id},
                       headers=auth("organizer2"))
        assert r.status_code == 200

    def test_a_session_that_does_not_exist_is_still_404(
        self, client: TestClient, auth
    ) -> None:
        r = client.put("/gate/shift", json={"showing_id": 999999999},
                       headers=auth("organizer"))
        assert r.status_code == 404

    def test_customer_never_opens_the_gate(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        r = client.put("/gate/shift", json={"showing_id": showing.id},
                       headers=auth("customer"))
        assert r.status_code == 403

    def test_cancelled_sessions_are_not_offered(
        self, client: TestClient, auth, gate_hired: User, showing: Showing
    ) -> None:
        """Sessão cancelada não recebe ninguém, então não é turno possível."""
        client.post(f"/showings/{showing.id}/cancel",
                    json={"reason": "Projetor quebrado"},
                    headers=auth("organizer"))

        ids = [s["showing_id"] for s in
               client.get("/gate/showings", headers=auth("gate")).json()]
        assert showing.id not in ids


class TestListingGates:
    def test_organizer_sees_the_staff(
        self, client: TestClient, auth, gate_bound: User
    ) -> None:
        r = client.get("/gates", headers=auth("organizer"))
        assert r.status_code == 200
        assert gate_bound.id in [g["id"] for g in r.json()]

    def test_staff_is_not_split_between_organizers(
        self, client: TestClient, auth, gate_bound: User
    ) -> None:
        """Consequência declarada de `Venue` não ter dono (D22).

        Recortar a equipe por organizador seria cerca isolada em volta de
        terreno aberto: qualquer organizador já cadastra cinema e cria sala
        em cinema alheio. A listagem concorda com o que a edição permite.
        """
        r = client.get("/gates", headers=auth("organizer2"))
        assert gate_bound.id in [g["id"] for g in r.json()]

    def test_gates_without_a_venue_are_listed(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        """São elas que precisam de atenção: o cadastro ficou pela metade."""
        assert users["gate"].gate_venue_id is None

        r = client.get("/gates", headers=auth("organizer"))
        assert users["gate"].id in [g["id"] for g in r.json()]


class TestEditingAndRemovingStaff:
    """Cadastro errado precisa de conserto, e conta que não serve mais, de saída."""

    def test_organizer_renames_an_employee(
        self, client: TestClient, auth, gate_hired: User
    ) -> None:
        r = client.patch(f"/gates/{gate_hired.id}", json={"name": "João da Porta"},
                         headers=auth("organizer"))
        assert r.status_code == 200
        assert r.json()["name"] == "João da Porta"

    def test_changing_venue_ends_the_shift(
        self, client: TestClient, auth, db: Session, gate_bound: User,
        room: Room
    ) -> None:
        """A sessão atendida é de outro lugar; manter deixaria a conta
        validando ingresso de um cinema onde a pessoa não trabalha mais."""
        outro = Venue(name="Cine Novo", city="Santos", city_ibge_id=3548500,
                      state="SP", address="Av. Ana Costa, 1")
        db.add(outro)
        db.commit()

        assert gate_bound.gate_showing_id is not None

        r = client.patch(f"/gates/{gate_bound.id}", json={"venue_id": outro.id},
                         headers=auth("organizer"))

        assert r.status_code == 200
        assert r.json()["showing_id"] is None

    def test_removing_the_venue_stops_validation(
        self, client: TestClient, auth, gate_bound: User, qr: str
    ) -> None:
        client.patch(f"/gates/{gate_bound.id}", json={"venue_id": None},
                     headers=auth("organizer"))

        r = client.post("/gate/validations", json={"code": qr},
                        headers=auth("gate"))
        assert r.status_code == 409

    def test_organizer_deletes_an_employee(
        self, client: TestClient, auth, db: Session, gate_hired: User
    ) -> None:
        alvo = gate_hired.id
        r = client.delete(f"/gates/{alvo}", headers=auth("organizer"))

        assert r.status_code == 204
        assert db.get(User, alvo) is None

    def test_employee_who_validated_cannot_be_deleted(
        self, client: TestClient, auth, gate_bound: User, qr: str
    ) -> None:
        """`validated_by` aponta para quem estava na porta (D24)."""
        assert validar(client, auth, qr)["result"] == "valid"

        r = client.delete(f"/gates/{gate_bound.id}", headers=auth("organizer"))
        assert r.status_code == 409

    def test_unknown_employee_is_404(
        self, client: TestClient, auth
    ) -> None:
        r = client.patch("/gates/999999999", json={"name": "Ninguém"},
                         headers=auth("organizer"))
        assert r.status_code == 404

    def test_a_customer_account_is_not_an_employee(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        """A rota é de equipe: cliente não é editável por ela."""
        r = client.delete(f"/gates/{users['customer'].id}",
                          headers=auth("organizer"))
        assert r.status_code == 404

    def test_employee_cannot_edit_itself(
        self, client: TestClient, auth, gate_hired: User
    ) -> None:
        """Escolher o próprio cinema é escolher quais ingressos aceitar."""
        r = client.patch(f"/gates/{gate_hired.id}", json={"name": "Eu mesmo"},
                         headers=auth("gate"))
        assert r.status_code == 403


class TestCoverage:
    """A pergunta de quem opera: qual sessão está sem ninguém na porta."""

    @pytest.fixture
    def daqui_a_pouco(
        self, db: Session, showing: Showing, room: Room
    ) -> Showing:
        """Dentro da janela da cobertura, ao contrário da sessão de amanhã."""
        return _sessao(db, showing.event_id, room, horas=2)

    def test_session_without_staff_is_listed_empty(
        self, client: TestClient, auth, daqui_a_pouco: Showing
    ) -> None:
        r = client.get("/gates/coverage", headers=auth("organizer"))
        assert r.status_code == 200

        alvo = next(c for c in r.json()
                    if c["showing"]["showing_id"] == daqui_a_pouco.id)
        assert alvo["staff"] == []

    def test_staff_on_shift_appears_on_their_session(
        self, client: TestClient, auth, db: Session, gate_hired: User,
        daqui_a_pouco: Showing
    ) -> None:
        gate_hired.gate_showing_id = daqui_a_pouco.id
        db.commit()

        r = client.get("/gates/coverage", headers=auth("organizer"))
        alvo = next(c for c in r.json()
                    if c["showing"]["showing_id"] == daqui_a_pouco.id)
        assert alvo["staff"] == ["Portaria"]

    def test_ending_the_shift_uncovers_the_session(
        self, client: TestClient, auth, db: Session, gate_hired: User,
        daqui_a_pouco: Showing
    ) -> None:
        gate_hired.gate_showing_id = daqui_a_pouco.id
        db.commit()

        client.put("/gate/shift", json={"showing_id": None},
                   headers=auth("gate"))

        r = client.get("/gates/coverage", headers=auth("organizer"))
        alvo = next(c for c in r.json()
                    if c["showing"]["showing_id"] == daqui_a_pouco.id)
        assert alvo["staff"] == []

    def test_cancelled_sessions_are_not_listed(
        self, client: TestClient, auth, daqui_a_pouco: Showing
    ) -> None:
        """Sessão cancelada não recebe ninguém: cobri-la seria ruído."""
        client.post(f"/showings/{daqui_a_pouco.id}/cancel",
                    json={"reason": "Projetor quebrado"},
                    headers=auth("organizer"))

        r = client.get("/gates/coverage", headers=auth("organizer"))
        assert daqui_a_pouco.id not in [
            c["showing"]["showing_id"] for c in r.json()]

    def test_every_organizer_sees_the_same_coverage(
        self, client: TestClient, auth, daqui_a_pouco: Showing
    ) -> None:
        """Duas visões diferentes deixariam uma porta descoberta sem que
        ninguém visse — a cobertura é da operação inteira (D29)."""
        um = client.get("/gates/coverage", headers=auth("organizer")).json()
        outro = client.get("/gates/coverage", headers=auth("organizer2")).json()

        ids = [c["showing"]["showing_id"] for c in outro]
        assert daqui_a_pouco.id in ids
        assert [c["showing"]["showing_id"] for c in um] == ids

    def test_far_future_sessions_are_out_of_the_window(
        self, client: TestClient, auth, db: Session, showing: Showing,
        room: Room
    ) -> None:
        """Doze horas cobrem a noite; a semana inteira seria ruído."""
        distante = _sessao(db, showing.event_id, room, dias=3)

        r = client.get("/gates/coverage", headers=auth("organizer"))
        assert distante.id not in [c["showing"]["showing_id"] for c in r.json()]

    @pytest.mark.parametrize("papel", ["customer", "gate"])
    def test_only_organizer_sees_coverage(
        self, client: TestClient, auth, papel: str
    ) -> None:
        assert client.get("/gates/coverage",
                          headers=auth(papel)).status_code == 403
