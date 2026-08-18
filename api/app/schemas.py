"""Contratos de entrada e saída da API.

Separados dos modelos de propósito: o modelo descreve o que existe no banco,
o schema descreve o que atravessa a fronteira HTTP. Sem essa separação,
adicionar uma coluna interna a User exporia esse campo na resposta sem que
ninguém decidisse isso — password_hash seria o primeiro a vazar.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import EventStatus, OrderStatus, Role, SeatKind, TicketStatus
from app.validation import GateResult


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class PromoteIn(BaseModel):
    # Por e-mail e não por id: quem promove conhece a pessoa pelo endereço
    # com que ela se cadastrou, não por um número que a interface teria de
    # expor antes.
    email: EmailStr


class OrganizerUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Role
    gate_showing_id: int | None


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
    """O nome da cidade não entra por aqui.

    Só a UF e o código do município: o nome é resolvido no servidor contra a
    lista do IBGE. Aceitá-lo do cliente reabriria a porta que a D23 fecha —
    dois cadastros escrevendo "São Paulo" e "sao paulo" para o mesmo lugar.
    """

    name: str = Field(min_length=2, max_length=255)
    state: str = Field(min_length=2, max_length=2, description="UF")
    city_ibge_id: int = Field(gt=0, description="Código do município no IBGE")
    address: str = Field(min_length=4, max_length=255)

    # Só é olhado quando o IBGE não responde: aí o nome vem daqui, porque a
    # alternativa seria não conseguir cadastrar cinema nenhum enquanto um
    # serviço de terceiro estiver fora (D28). Com o IBGE no ar este campo é
    # ignorado — o nome oficial sempre vence.
    city_fallback: str | None = Field(default=None, min_length=2, max_length=120)

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
    city_ibge_id: int
    state: str
    address: str


class UfOut(BaseModel):
    sigla: str
    nome: str


class MunicipioOut(BaseModel):
    id: int
    nome: str


class CityOut(BaseModel):
    """Uma cidade com cinema, para o filtro do catálogo.

    Traz a UF junto porque nome de cidade se repete entre estados, e o
    cliente precisa distinguir qual "Bom Jesus" está vendo (D23).
    """

    id: int
    nome: str
    uf: str


class VenueUpdate(BaseModel):
    """Campos editáveis de um cinema.

    A cidade só muda em par: mandar a UF sem o município deixaria o código
    apontando para outro estado, que é o erro que a D23 fecha.
    """

    name: str | None = Field(default=None, min_length=2, max_length=255)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    city_ibge_id: int | None = Field(default=None, gt=0)
    address: str | None = Field(default=None, min_length=4, max_length=255)

    @field_validator("state")
    @classmethod
    def uf_maiuscula(cls, v: str | None) -> str | None:
        return v.upper() if v else v


class RoomUpdate(BaseModel):
    """Campos editáveis de uma sala.

    O layout continua editável mesmo com sessões marcadas: os assentos
    pertencem à exibição e são gerados na publicação, então a mudança vale
    para as próximas e não reescreve mapa já vendido (D6).
    """

    name: str | None = Field(default=None, min_length=1, max_length=60)
    rows: int | None = Field(default=None, ge=1, le=26)
    seats_per_row: int | None = Field(default=None, ge=1, le=40)


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
    """Traz o local resolvido, não só o id da sala.

    O catálogo precisa exibir data, local e preço; sem o nome do cinema aqui,
    o front faria uma consulta por filme só para descobri-lo.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    room_id: int
    starts_at: datetime
    audio: str
    price_cents: int

    venue_name: str
    venue_city: str
    venue_address: str
    room_name: str
    seats_available: int
    seats_total: int

    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None

    # A tela de assentos exibe o filme junto do mapa. Sem estes campos ela
    # faria uma segunda requisição só para descobrir o título.
    event_title: str
    poster_url: str | None
    runtime_minutes: int | None


class CatalogEventOut(BaseModel):
    """Filme em cartaz com suas sessões, numa requisição só."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    synopsis: str | None
    poster_url: str | None
    backdrop_url: str | None
    runtime_minutes: int | None
    showings: list[ShowingOut]


class CancelIn(BaseModel):
    reason: str = Field(min_length=3, max_length=255,
                        description="Aparece para quem tem ingresso")


class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    row_label: str
    number: int
    kind: SeatKind
    label: str

    # Ocupado cobre vendido e em checkout. O cliente não precisa saber a
    # diferença: nos dois casos a poltrona não está disponível para ele.
    taken: bool = False


# ------------------------------------------------------------ reserva


class ReservationIn(BaseModel):
    seat_ids: list[int] = Field(min_length=1, max_length=10)


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jti: str
    status: TicketStatus

    # O mapa precisa cruzar ingresso e poltrona para marcar como "sua" o que
    # o próprio cliente reservou. Cruzar por rótulo funcionaria, mas amarraria
    # a interface a comparar texto.
    seat_id: int
    seat_label: str
    row_label: str
    number: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    showing_id: int
    status: OrderStatus
    total_cents: int
    held_until: datetime | None
    tickets: list[TicketOut]


class PaymentIn(BaseModel):
    card_number: str = Field(min_length=13, max_length=25)
    holder_name: str = Field(min_length=2, max_length=120)


class PaymentOut(BaseModel):
    approved: bool
    reason: str | None
    order: OrderOut


class MyTicketOut(BaseModel):
    """Ingresso na área do cliente, com o conteúdo do QR."""

    id: int
    jti: str
    status: TicketStatus
    seat_label: str
    qr_token: str

    event_title: str
    poster_url: str | None
    venue_name: str
    # O endereço é o dado que o bilhete existe para carregar no dia: sem ele
    # a pessoa sai de casa com o nome do cinema e nada mais.
    venue_address: str
    venue_city: str
    room_name: str
    starts_at: datetime
    audio: str
    price_cents: int

    # Quem tem ingresso de sessão cancelada precisa achar a explicação onde
    # procuraria o ingresso.
    showing_cancelled: bool = False
    cancellation_reason: str | None = None


# ---------------------------------------------------- portaria


class ShowingBriefOut(BaseModel):
    """Uma exibição em uma linha, para a portaria."""

    model_config = ConfigDict(from_attributes=True)

    # Preenchido na lista de turnos, onde serve para escolher. Ausente no
    # veredito de validação, que descreve a sessão sem precisar apontá-la.
    showing_id: int | None = None

    event_id: int
    event_title: str
    starts_at: datetime
    venue_name: str
    venue_city: str
    room_name: str


class ValidationIn(BaseModel):
    # Um campo só para o QR lido e para o código digitado: quem valida não
    # deveria ter de declarar por qual caminho o código chegou.
    code: str = Field(min_length=1, max_length=2000)


class ValidationOut(BaseModel):
    result: GateResult

    seat_label: str | None = None
    customer_name: str | None = None

    # A exibição a que o ingresso pertence. Nos desfechos recusados é ela que
    # diz a quem foi barrado onde o ingresso vale.
    showing: ShowingBriefOut | None = None

    used_at: datetime | None = None


class GateOut(BaseModel):
    """Uma conta de portaria: onde trabalha e o que atende agora."""

    id: int
    name: str
    email: EmailStr

    # O cinema é o escopo do emprego e quem define é o organizador.
    venue_id: int | None
    venue_name: str | None

    # A sessão é o turno, e quem escolhe é o próprio funcionário (D24).
    showing_id: int | None
    showing: ShowingBriefOut | None


class GateIn(BaseModel):
    """Conta de uma pessoa, não de um posto.

    Sem sessão: quem escolhe o turno é quem trabalha. O organizador define
    apenas o cinema, que é o que a conta nunca deixa de ser (D24).
    """

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class CoverageOut(BaseModel):
    """Uma sessão e quem está na porta dela.

    A lista vazia é o dado que importa: sessão prestes a começar sem
    ninguém atendendo é o que o organizador precisa ver antes que a fila se
    forme (D26).
    """

    showing: ShowingBriefOut
    staff: list[str]


class GateUpdate(BaseModel):
    """O que o organizador edita numa conta de funcionário.

    Nome e cinema, nunca a senha: trocá-la pelo painel obrigaria a entregar
    a nova por algum canal, que é o problema que a promoção evita (D22).
    """

    name: str | None = Field(default=None, min_length=2, max_length=120)
    venue_id: int | None = None

    # Escalar alguém para uma sessão sem depender de ele estar com o
    # aparelho na mão. O caminho normal continua sendo a escolha do próprio
    # funcionário (D24); este é o remanejamento de quem coordena.
    showing_id: int | None = None


class GateShiftIn(BaseModel):
    # Nulo encerra o turno: a conta continua existindo e para de validar, que
    # é o que se quer entre uma sessão e a seguinte.
    showing_id: int | None


# ---------------------------------------------------- compartilhamento


class ShareLinkOut(BaseModel):
    token: str
    revoked: bool
    created_at: datetime


class SharedTicketOut(BaseModel):
    """Ingresso visto por quem recebeu o link.

    Sem o nome de quem comprou: o link circula por mensagem e pode chegar a
    mais gente do que o titular pretendia.
    """

    status: TicketStatus
    seat_label: str
    qr_token: str

    event_title: str
    poster_url: str | None
    venue_name: str
    venue_address: str
    venue_city: str
    room_name: str
    starts_at: datetime
    audio: str
