import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Role(str, enum.Enum):
    ORGANIZER = "organizer"
    CUSTOMER = "customer"
    GATE = "gate"


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class SeatKind(str, enum.Enum):
    STANDARD = "standard"
    ACCESSIBLE = "accessible"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUSED = "refused"
    CANCELLED = "cancelled"


class TicketStatus(str, enum.Enum):
    HELD = "held"
    VALID = "valid"
    USED = "used"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(String(20))

    # Só para papel GATE: o evento que este usuário está autorizado a validar.
    # É o que permite distinguir "ingresso de outro evento" de "inválido".
    # use_alter porque users e events se referenciam mutuamente: o Postgres
    # precisa criar as duas tabelas antes de amarrar esta chave.
    gate_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL", use_alter=True,
                   name="fk_users_gate_event")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    tmdb_id: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    synopsis: Mapped[str | None] = mapped_column(Text)
    poster_url: Mapped[str | None] = mapped_column(String(500))
    backdrop_url: Mapped[str | None] = mapped_column(String(500))
    runtime_minutes: Mapped[int | None] = mapped_column(Integer)

    # O local não fica aqui: ele é propriedade da sala, e a sala vem pela
    # exibição. Um mesmo filme pode ser exibido em cinemas diferentes.
    status: Mapped[EventStatus] = mapped_column(String(20), default=EventStatus.DRAFT)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    showings: Mapped[list["Showing"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class Room(Base):
    """Uma sala física. O layout é propriedade dela, não da exibição."""

    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("venue", "name", name="uq_room_no_local"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # O cinema. Texto e não tabela própria: neste escopo o local não tem
    # atributo nenhum além do nome, e uma tabela de um campo só não carrega
    # informação que o texto já não carregue.
    venue: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(60))

    rows: Mapped[int] = mapped_column(Integer, default=8)
    seats_per_row: Mapped[int] = mapped_column(Integer, default=12)

    showings: Mapped[list["Showing"]] = relationship(back_populates="room")

    @property
    def capacity(self) -> int:
        return self.rows * self.seats_per_row


class Showing(Base):
    """Uma exibição: o mesmo filme em sala, data e preço específicos."""

    __tablename__ = "showings"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))

    # RESTRICT: apagar uma sala com exibições agendadas deve falhar, não
    # apagar as exibições em cascata nem deixar a sessão sem lugar.
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="RESTRICT"), index=True
    )

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    audio: Mapped[str] = mapped_column(String(30), default="Dublado")

    # Dinheiro em centavos: inteiro não acumula erro de arredondamento.
    price_cents: Mapped[int] = mapped_column(Integer)

    event: Mapped["Event"] = relationship(back_populates="showings")
    room: Mapped["Room"] = relationship(back_populates="showings")
    seats: Mapped[list["Seat"]] = relationship(
        back_populates="showing", cascade="all, delete-orphan"
    )


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("showing_id", "row_label", "number", name="uq_seat_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    showing_id: Mapped[int] = mapped_column(
        ForeignKey("showings.id", ondelete="CASCADE"), index=True
    )

    row_label: Mapped[str] = mapped_column(String(2))
    number: Mapped[int] = mapped_column(Integer)
    kind: Mapped[SeatKind] = mapped_column(String(20), default=SeatKind.STANDARD)

    showing: Mapped["Showing"] = relationship(back_populates="seats")

    @property
    def label(self) -> str:
        return f"{self.row_label}{self.number}"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    showing_id: Mapped[int] = mapped_column(ForeignKey("showings.id"))

    status: Mapped[OrderStatus] = mapped_column(String(20), default=OrderStatus.PENDING)
    total_cents: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="order")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        # A garantia central do sistema: um assento não pode ter dois ingressos
        # vivos. Parcial para que o cancelamento devolva o assento ao estoque.
        # O índice é criado com a cláusula WHERE na migration do Alembic.
        Index(
            "uq_seat_ocupado",
            "seat_id",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"))

    # Identificador público do ingresso. Vai dentro do QR assinado e é o que
    # o cliente digita na portaria quando a câmera falha.
    jti: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )

    status: Mapped[TicketStatus] = mapped_column(String(20), default=TicketStatus.HELD)

    # Enquanto HELD, o assento está travado até este instante.
    held_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    order: Mapped["Order"] = relationship(back_populates="tickets")
    seat: Mapped["Seat"] = relationship()


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)

    # Token opaco e revogável, separado da assinatura do ingresso: revogar um
    # compartilhamento não pode invalidar o ingresso em si.
    token: Mapped[str] = mapped_column(
        String(43), unique=True, index=True
    )
    revoked: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
