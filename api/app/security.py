"""Primitivas de senha e token.

O mesmo segredo assina a sessão do usuário e o código do ingresso, mas os
dois têm formatos distintos e são verificados por caminhos distintos —
misturá-los permitiria usar um ingresso como credencial de acesso.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config import get_settings

ALGORITHM = "HS256"

# Distingue os dois tipos de token emitidos com a mesma chave. Um token de
# ingresso apresentado como credencial de login é rejeitado por este campo.
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_TICKET = "ticket"


def hash_password(plain: str) -> str:
    # bcrypt trunca em 72 bytes silenciosamente; cortar antes deixa o limite
    # explícito em vez de depender do comportamento da biblioteca.
    return bcrypt.hashpw(plain.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:72], hashed.encode())
    except ValueError:
        # Hash malformado no banco não deve derrubar a requisição.
        return False


def create_access_token(user_id: int, role: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": TOKEN_TYPE_ACCESS,
        "iat": now,
        "exp": now + timedelta(hours=settings.access_token_hours),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_ticket_token(jti: str, event_id: int) -> str:
    """O conteúdo do QR.

    Sem prazo de validade de propósito: quem decide se o ingresso vale é a
    portaria consultando o banco. Expiração aqui criaria uma segunda fonte de
    verdade sobre validade, e duas fontes divergem.

    O event_id vai dentro para que a portaria distinga "evento errado" de
    "inválido" sem precisar de consulta extra antes de decidir.
    """
    return jwt.encode(
        {"jti": jti, "evt": event_id, "type": TOKEN_TYPE_TICKET},
        get_settings().secret_key,
        algorithm=ALGORITHM,
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any] | None:
    """Devolve o payload, ou None se assinatura, validade ou tipo não conferem."""
    try:
        payload = jwt.decode(
            token, get_settings().secret_key, algorithms=[ALGORITHM]
        )
    except jwt.InvalidTokenError:
        # Cobre assinatura inválida, expiração e formato corrompido. Não
        # distinguimos os casos na resposta: dizer "expirado" em vez de
        # "inválido" entrega informação a quem está tentando forjar.
        return None

    if payload.get("type") != expected_type:
        return None
    return payload
