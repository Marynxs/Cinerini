"""Contratos de entrada e saída da API.

Separados dos modelos de propósito: o modelo descreve o que existe no banco,
o schema descreve o que atravessa a fronteira HTTP. Sem essa separação,
adicionar uma coluna interna a User exporia esse campo na resposta sem que
ninguém decidisse isso — password_hash seria o primeiro a vazar.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Role


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Role
    gate_event_id: int | None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
