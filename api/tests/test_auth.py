"""Cadastro, login e autorização por papel."""

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Event, Showing, User
from app.security import TOKEN_TYPE_TICKET, create_access_token

from .conftest import SENHA

NOVO = {"name": "Ana Prado", "email": "ana@cinerini.com.br",
        "password": "senhaForte123"}


class TestRegister:
    def test_creates_account_and_returns_token(self, client: TestClient) -> None:
        r = client.post("/auth/register", json=NOVO)
        assert r.status_code == 201
        assert r.json()["access_token"]

    def test_always_creates_a_customer(self, client: TestClient) -> None:
        """Aceitar o papel do corpo deixaria qualquer visitante virar organizador."""
        r = client.post("/auth/register", json={**NOVO, "role": "organizer"})
        assert r.json()["user"]["role"] == "customer"

    def test_never_returns_the_password(self, client: TestClient) -> None:
        r = client.post("/auth/register", json=NOVO)
        assert "senhaForte123" not in r.text
        assert "password_hash" not in r.text

    def test_stores_password_as_bcrypt_hash(
        self, client: TestClient, db: Session
    ) -> None:
        client.post("/auth/register", json=NOVO)
        guardado = db.scalar(
            select(User.password_hash).where(User.email == NOVO["email"])
        )
        assert guardado.startswith("$2b$")
        assert NOVO["password"] not in guardado

    def test_duplicate_email_is_rejected(self, client: TestClient) -> None:
        client.post("/auth/register", json=NOVO)
        assert client.post("/auth/register", json=NOVO).status_code == 409

    @pytest.mark.parametrize("campo,valor", [
        ("password", "curta"),
        ("email", "nao-e-email"),
        ("name", "A"),
    ])
    def test_invalid_input_is_rejected(
        self, client: TestClient, campo: str, valor: str
    ) -> None:
        assert client.post(
            "/auth/register", json={**NOVO, campo: valor}
        ).status_code == 422


class TestLogin:
    def test_correct_credentials_return_token(
        self, client: TestClient, users: dict[str, User]
    ) -> None:
        r = client.post("/auth/login",
                        json={"email": users["customer"].email, "password": SENHA})
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "customer"

    def test_wrong_password_and_unknown_email_look_identical(
        self, client: TestClient, users: dict[str, User]
    ) -> None:
        """Distinguir os dois revelaria quais e-mails têm conta."""
        senha_errada = client.post(
            "/auth/login",
            json={"email": users["customer"].email, "password": "outraSenha123"},
        )
        inexistente = client.post(
            "/auth/login",
            json={"email": "ninguem@cinerini.com.br", "password": SENHA},
        )

        assert senha_errada.status_code == inexistente.status_code == 401
        assert senha_errada.json()["detail"] == inexistente.json()["detail"]


class TestProtectedRoute:
    def test_without_token_is_unauthorized(self, client: TestClient) -> None:
        assert client.get("/auth/me").status_code == 401

    def test_garbage_token_is_unauthorized(self, client: TestClient) -> None:
        assert client.get(
            "/auth/me", headers={"Authorization": "Bearer lixo"}
        ).status_code == 401

    def test_valid_token_identifies_the_user(self, client: TestClient, auth) -> None:
        r = client.get("/auth/me", headers=auth("customer"))
        assert r.status_code == 200
        assert r.json()["email"] == "cli@cinerini.com.br"


class TestTokenIntegrity:
    def test_tampered_signature_is_rejected(self, client: TestClient, auth) -> None:
        token = auth("customer")["Authorization"].removeprefix("Bearer ")
        cabecalho, corpo, assinatura = token.split(".")
        forjado = f"{cabecalho}.{corpo}.{'a' * len(assinatura)}"

        assert client.get(
            "/auth/me", headers={"Authorization": f"Bearer {forjado}"}
        ).status_code == 401

    def test_token_signed_with_another_key_is_rejected(
        self, client: TestClient
    ) -> None:
        outro = jwt.encode({"sub": "1", "role": "organizer", "type": "access"},
                           "chave-errada", algorithm="HS256")
        assert client.get(
            "/auth/me", headers={"Authorization": f"Bearer {outro}"}
        ).status_code == 401

    def test_ticket_token_does_not_work_as_credential(
        self, client: TestClient
    ) -> None:
        """O campo 'type' separa os dois usos da mesma chave."""
        ingresso = jwt.encode(
            {"sub": "1", "role": "customer", "type": TOKEN_TYPE_TICKET},
            get_settings().secret_key, algorithm="HS256",
        )
        assert client.get(
            "/auth/me", headers={"Authorization": f"Bearer {ingresso}"}
        ).status_code == 401

    def test_role_comes_from_database_not_from_token(
        self, client: TestClient, users: dict[str, User]
    ) -> None:
        """Token forjado com papel elevado não eleva ninguém."""
        mentiroso = create_access_token(users["customer"].id, "organizer")

        r = client.get("/auth/me",
                       headers={"Authorization": f"Bearer {mentiroso}"})
        assert r.status_code == 200
        assert r.json()["role"] == "customer"


class TestRoleAuthorization:
    @pytest.mark.parametrize("papel,esperado", [
        ("organizer", 200), ("customer", 403), ("gate", 403),
    ])
    def test_catalog_search_is_organizer_only(
        self, client: TestClient, auth, fake_tmdb, papel: str, esperado: int
    ) -> None:
        r = client.get("/catalog/search", params={"q": "duna"},
                       headers=auth(papel))
        assert r.status_code == esperado


def _esvaziar(db: Session) -> None:
    """Deixa o banco como uma instalação recém-criada.

    A ordem vem do próprio seed em vez de ser repetida aqui: são as mesmas
    dependências, e duas listas para a mesma coisa divergem. Roda dentro da
    transação do teste, que é desfeita no fim.
    """
    from app.seed import TABELAS

    for tabela in TABELAS:
        db.execute(text(f"DELETE FROM {tabela}"))
    db.commit()


class TestFirstAccount:
    """Instalação vazia precisa de um caminho para o primeiro organizador."""

    def test_first_signup_becomes_organizer(
        self, client: TestClient, db: Session
    ) -> None:
        """Sem isto, um clone recém-instalado nasce sem ninguém que publique."""
        _esvaziar(db)

        r = client.post("/auth/register", json={
            "name": "Primeiro", "email": "primeiro@cinerini.com.br",
            "password": "senhaForte123"})

        assert r.status_code == 201
        assert r.json()["user"]["role"] == "organizer"

    def test_second_signup_is_a_customer(
        self, client: TestClient, db: Session
    ) -> None:
        """A porta se fecha no primeiro cadastro e nunca reabre (D22)."""
        _esvaziar(db)

        client.post("/auth/register", json={
            "name": "Primeiro", "email": "primeiro@cinerini.com.br",
            "password": "senhaForte123"})

        r = client.post("/auth/register", json={
            "name": "Segundo", "email": "segundo@cinerini.com.br",
            "password": "senhaForte123"})

        assert r.json()["user"]["role"] == "customer"

    def test_signup_is_a_customer_when_users_exist(
        self, client: TestClient, users: dict[str, User]
    ) -> None:
        r = client.post("/auth/register", json={
            "name": "Comum", "email": "comum@cinerini.com.br",
            "password": "senhaForte123"})

        assert r.json()["user"]["role"] == "customer"


class TestPromotion:
    """Organizador é promovido por outro, nunca criado com senha inventada."""

    def test_organizer_promotes_an_employee(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        r = client.post("/auth/organizers",
                        json={"email": users["gate"].email},
                        headers=auth("organizer"))

        assert r.status_code == 200
        assert r.json()["role"] == "organizer"

    def test_promotion_drops_the_gate_assignment(
        self, client: TestClient, auth, db: Session, gate_hired: User
    ) -> None:
        """Os papéis são exclusivos: quem publica não valida na porta."""
        assert gate_hired.gate_venue_id is not None

        client.post("/auth/organizers", json={"email": gate_hired.email},
                    headers=auth("organizer"))
        db.refresh(gate_hired)

        assert gate_hired.gate_venue_id is None
        assert gate_hired.gate_showing_id is None

    def test_promoted_account_keeps_validating_by_the_new_role(
        self, client: TestClient, auth, gate_hired: User
    ) -> None:
        """Promovido não perde a porta: o organizador também a abre (D27).

        O que muda é o escopo — deixa de ser o cinema onde trabalhava e passa
        a ser o catálogo que publica. Sem turno escolhido, a resposta é 409
        de configuração, não 403 de acesso.
        """
        client.post("/auth/organizers", json={"email": gate_hired.email},
                    headers=auth("organizer"))

        r = client.post("/gate/validations", json={"code": "x"},
                        headers=auth("gate"))
        assert r.status_code == 409

    def test_customer_is_promotable_too(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        r = client.post("/auth/organizers",
                        json={"email": users["customer"].email},
                        headers=auth("organizer"))
        assert r.status_code == 200

    def test_promoting_twice_is_refused(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        r = client.post("/auth/organizers",
                        json={"email": users["organizer2"].email},
                        headers=auth("organizer"))
        assert r.status_code == 409

    def test_unknown_email_is_refused(
        self, client: TestClient, auth
    ) -> None:
        """Promover não cria conta: a pessoa se cadastra sozinha antes."""
        r = client.post("/auth/organizers",
                        json={"email": "ninguem@cinerini.com.br"},
                        headers=auth("organizer"))
        assert r.status_code == 404

    @pytest.mark.parametrize("papel", ["customer", "gate"])
    def test_only_organizer_promotes(
        self, client: TestClient, auth, users: dict[str, User], papel: str
    ) -> None:
        r = client.post("/auth/organizers",
                        json={"email": users["customer2"].email},
                        headers=auth(papel))
        assert r.status_code == 403


class TestEditingOrganizers:
    """O quadro de organizadores também se corrige."""

    def test_renames_an_organizer(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        r = client.patch(f"/auth/organizers/{users['organizer2'].id}",
                         json={"name": "Marina Corrigida"},
                         headers=auth("organizer"))
        assert r.status_code == 200
        assert r.json()["name"] == "Marina Corrigida"

    def test_the_first_organizer_is_editable(
        self, client: TestClient, auth, db: Session, users: dict[str, User]
    ) -> None:
        """Intocável para remoção, não para correção de cadastro (D27)."""
        primeiro = db.scalar(
            select(User).where(User.role == "organizer").order_by(User.id).limit(1))

        r = client.patch(f"/auth/organizers/{primeiro.id}",
                         json={"name": "Primeiro Renomeado"},
                         headers=auth("organizer"))
        assert r.status_code == 200

    def test_a_customer_is_not_an_organizer(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        r = client.patch(f"/auth/organizers/{users['customer'].id}",
                         json={"name": "Xisto"}, headers=auth("organizer"))
        assert r.status_code == 404

    def test_only_organizer_edits(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        r = client.patch(f"/auth/organizers/{users['organizer2'].id}",
                         json={"name": "Xisto"}, headers=auth("customer"))
        assert r.status_code == 403


class TestDemotingOrganizers:
    """Revoga o papel; não apaga a conta nem o que ela publicou."""

    def test_demotion_turns_the_account_into_a_customer(
        self, client: TestClient, auth, db: Session, users: dict[str, User]
    ) -> None:
        r = client.delete(f"/auth/organizers/{users['organizer2'].id}",
                          headers=auth("organizer"))

        assert r.status_code == 200
        assert r.json()["role"] == "customer"

    def test_demotion_keeps_the_account_and_its_events(
        self, client: TestClient, auth, db: Session, users: dict[str, User],
        showing: Showing
    ) -> None:
        """Apagar levaria junto sessões e ingressos vendidos (D27)."""
        dono = users["organizer"].id
        client.delete(f"/auth/organizers/{users['organizer2'].id}",
                      headers=auth("organizer"))

        assert db.get(User, users["organizer2"].id) is not None
        assert db.get(Showing, showing.id) is not None
        assert db.scalar(select(Event.organizer_id)
                         .where(Event.id == showing.event_id)) == dono

    def test_the_first_organizer_cannot_be_demoted(
        self, client: TestClient, auth, db: Session
    ) -> None:
        """É ele que impede a instalação de ficar sem ninguém que publique."""
        primeiro = db.scalar(
            select(User).where(User.role == "organizer").order_by(User.id).limit(1))

        r = client.delete(f"/auth/organizers/{primeiro.id}",
                          headers=auth("organizer"))
        assert r.status_code == 409

    def test_cannot_demote_yourself(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        """O clique seria irreversível pela própria tela."""
        r = client.delete(f"/auth/organizers/{users['organizer2'].id}",
                          headers=auth("organizer2"))
        assert r.status_code == 409

    def test_demoted_account_loses_the_panel(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        client.delete(f"/auth/organizers/{users['organizer2'].id}",
                      headers=auth("organizer"))

        assert client.get("/events/managed",
                          headers=auth("organizer2")).status_code == 403

    def test_only_organizer_demotes(
        self, client: TestClient, auth, users: dict[str, User]
    ) -> None:
        r = client.delete(f"/auth/organizers/{users['organizer2'].id}",
                          headers=auth("customer"))
        assert r.status_code == 403
