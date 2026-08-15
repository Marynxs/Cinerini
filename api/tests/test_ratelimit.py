"""Limite de tentativas: a janela deslizante e seu efeito nas rotas."""

import time

from fastapi.testclient import TestClient

from app.models import User
from app.ratelimit import SlidingWindow, login_by_account

from .conftest import SENHA


class TestSlidingWindow:
    def test_allows_up_to_the_limit(self) -> None:
        w = SlidingWindow(limit=3, window_seconds=60)
        assert [w.check("a") for _ in range(3)] == [0, 0, 0]

    def test_blocks_past_the_limit_and_says_how_long(self) -> None:
        w = SlidingWindow(limit=1, window_seconds=60)
        w.check("a")
        assert w.check("a") > 0

    def test_keys_do_not_interfere(self) -> None:
        w = SlidingWindow(limit=1, window_seconds=60)
        w.check("a")
        assert w.check("b") == 0

    def test_window_slides(self) -> None:
        w = SlidingWindow(limit=1, window_seconds=1)
        w.check("a")
        time.sleep(1.1)
        assert w.check("a") == 0

    def test_expired_key_leaves_memory(self) -> None:
        """Chave vazia acumulando seria vazamento com gatilho externo."""
        w = SlidingWindow(limit=1, window_seconds=1)
        w.check("a")
        time.sleep(1.1)
        w.check("a")
        assert len(w._hits) == 1

    def test_reset_releases_the_key(self) -> None:
        w = SlidingWindow(limit=1, window_seconds=60)
        w.check("a")
        w.reset("a")
        assert w.check("a") == 0


class TestLoginBruteForce:
    """A defesa real é por conta: não adianta o atacante trocar de IP."""

    def _tentar(self, client: TestClient, email: str, senha: str):
        return client.post("/auth/login", json={"email": email, "password": senha})

    def test_account_is_locked_after_repeated_failures(
        self, client: TestClient, users: dict[str, User]
    ) -> None:
        email = users["customer"].email
        codigos = [
            self._tentar(client, email, f"errada{i}").status_code
            for i in range(9)
        ]

        assert codigos[:8] == [401] * 8
        assert codigos[8] == 429

    def test_locked_account_rejects_even_the_right_password(
        self, client: TestClient, users: dict[str, User]
    ) -> None:
        email = users["customer"].email
        for i in range(9):
            self._tentar(client, email, f"errada{i}")

        r = self._tentar(client, email, SENHA)
        assert r.status_code == 429
        assert "retry-after" in {k.lower() for k in r.headers}

    def test_success_clears_the_count(
        self, client: TestClient, users: dict[str, User]
    ) -> None:
        """Erro de digitação não pode punir quem sabe a senha."""
        email = users["customer"].email
        for i in range(5):
            self._tentar(client, email, f"errada{i}")

        assert self._tentar(client, email, SENHA).status_code == 200

        for i in range(8):
            r = self._tentar(client, email, f"outra{i}")
        assert r.status_code == 401

    def test_other_accounts_are_not_affected(
        self, client: TestClient, users: dict[str, User]
    ) -> None:
        for i in range(9):
            self._tentar(client, users["customer"].email, f"errada{i}")

        r = self._tentar(client, users["customer2"].email, "senhaQualquer123")
        assert r.status_code == 401


class TestRegisterFlood:
    def test_register_is_capped_per_address(self, client: TestClient) -> None:
        """Mitiga varredura de lista de e-mails atrás de quem tem conta."""
        codigos = []
        for i in range(21):
            r = client.post("/auth/register", json={
                "name": f"Usuario {i}",
                "email": f"u{i}@cinerini.com.br",
                "password": "senhaForte123",
            })
            codigos.append(r.status_code)

        assert codigos[:20] == [201] * 20
        assert codigos[20] == 429
