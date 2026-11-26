"""Configuração recusada na subida, antes de assinar o primeiro token."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_recusa_chave_menor_que_o_hash_do_hs256() -> None:
    """Garantia 2: chave curta torna o QR forjável por força bruta."""
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql+psycopg://x@y/z", secret_key="curta-demais")


def test_aceita_chave_de_32_bytes() -> None:
    s = Settings(database_url="postgresql+psycopg://x@y/z", secret_key="a" * 32)
    assert len(s.secret_key) == 32
