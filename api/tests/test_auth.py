"""Cadastro, login e autorização por papel."""

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.security import TOKEN_TYPE_TICKET, create_access_token

from .conftest import SENHA

NOVO = {"name": "Ana Prado", "email": "ana@bilheteria.com.br",
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
            json={"email": "ninguem@bilheteria.com.br", "password": SENHA},
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
        assert r.json()["email"] == "cli@bilheteria.com.br"


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
