"""Dependências de autenticação e autorização."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User
from app.security import TOKEN_TYPE_ACCESS, decode_token

bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais ausentes ou inválidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if creds is None:
        raise unauthorized

    payload = decode_token(creds.credentials, expected_type=TOKEN_TYPE_ACCESS)
    if payload is None:
        raise unauthorized

    user = db.get(User, int(payload["sub"]))
    if user is None:
        # Token válido de usuário removido. A assinatura confere, mas o
        # banco é a fonte de verdade sobre quem existe.
        raise unauthorized

    # O papel é relido do banco, não aceito do token: uma mudança de papel
    # passa a valer na hora, sem esperar o token expirar.
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed: Role):
    """Fábrica de dependency que restringe uma rota a determinados papéis."""

    def guard(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu perfil não tem acesso a esta operação.",
            )
        return user

    return guard


# Atalhos nomeados: a rota declara o papel exigido e a intenção fica legível
# na assinatura, sem repetir a construção em cada endpoint.
Organizer = Annotated[User, Depends(require_role(Role.ORGANIZER))]
Customer = Annotated[User, Depends(require_role(Role.CUSTOMER))]

# O organizador também abre a portaria (D27). Num cinema pequeno quem publica
# a sessão é quem fica na porta, e obrigá-lo a manter uma segunda conta só
# para validar seria burocracia sem ganho de segurança, porque ele já pode tudo o
# que a portaria pode, e mais.
Gate = Annotated[User, Depends(require_role(Role.GATE, Role.ORGANIZER))]
