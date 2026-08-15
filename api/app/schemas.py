"""Contratos de entrada e saída da API.

Separados dos modelos de propósito: o modelo descreve o que existe no banco,
o schema descreve o que atravessa a fronteira HTTP. Sem essa separação,
adicionar uma coluna interna a User exporia esse campo na resposta sem que
ninguém decidisse isso — password_hash seria o primeiro a vazar.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import EventStatus, Role, SeatKind


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


class TmdbSearchOut(BaseModel):
    tmdb_id: int
    title: str
    year: str | None
    synopsis: str | None
    poster_url: str | None


class TmdbDetailOut(BaseModel):
    tmdb_id: int
    title: str
    synopsis: str | None
    poster_url: str | None
    backdrop_url: str | None
    runtime_minutes: int | None


# ---------------------------------------------------------------- cinemas


class VenueIn(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    city: str = Field(min_length=2, max_length=120)
    state: str = Field(min_length=2, max_length=2, description="UF")
    address: str = Field(min_length=4, max_length=255)

    @field_validator("state")
    @classmethod
    def uf_maiuscula(cls, v: str) -> str:
        # Normalizado na entrada e não na rota: "sp" e "SP" são o mesmo
        # estado, e deixar as duas formas no banco quebraria filtro por UF.
        return v.upper()


class VenueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    city: str
    state: str
    address: str


class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    rows: int = Field(ge=1, le=26, description="Uma letra por fileira, de A a Z")
    seats_per_row: int = Field(ge=1, le=40)


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    venue_id: int
    name: str
    rows: int
    seats_per_row: int
    capacity: int


# ----------------------------------------------------------------- eventos


class EventIn(BaseModel):
    """Criado a partir do catálogo ou à mão.

    Com tmdb_id, os demais campos são preenchidos pelo catálogo e o que vier
    no corpo é ignorado — a origem é uma só. Sem tmdb_id, o título é
    obrigatório.
    """

    tmdb_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    synopsis: str | None = None
    poster_url: str | None = Field(default=None, max_length=500)
    backdrop_url: str | None = Field(default=None, max_length=500)
    runtime_minutes: int | None = Field(default=None, ge=1, le=1000)


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tmdb_id: int | None
    title: str
    synopsis: str | None
    poster_url: str | None
    backdrop_url: str | None
    runtime_minutes: int | None
    status: EventStatus


# ---------------------------------------------------------------- sessões


class ShowingIn(BaseModel):
    room_id: int
    starts_at: datetime
    price_cents: int = Field(ge=0, le=100_000, description="Em centavos")
    audio: str = Field(default="Dublado", max_length=30)


class ShowingUpdate(BaseModel):
    """Campos editáveis depois de criada. Ver decisão D9 quanto à sala."""

    room_id: int | None = None
    starts_at: datetime | None = None
    price_cents: int | None = Field(default=None, ge=0, le=100_000)
    audio: str | None = Field(default=None, max_length=30)


class ShowingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    room_id: int
    starts_at: datetime
    audio: str
    price_cents: int


class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    row_label: str
    number: int
    kind: SeatKind
