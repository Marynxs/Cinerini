"""Mapa de assentos de uma exibição: geração e disponibilidade."""

from datetime import datetime, timezone
from string import ascii_uppercase

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Seat, SeatKind, Showing, Ticket, TicketStatus


def generate_seats(db: Session, showing: Showing) -> int:
    """Cria as poltronas a partir do layout da sala. Devolve quantas criou.

    Fileira A é a mais próxima da tela, e é onde ficam as duas poltronas
    acessíveis: o piso ali é plano, sem os degraus da arquibancada, e a
    entrada da sala dá nesse nível.
    """
    room = showing.room

    seats = [
        Seat(
            showing_id=showing.id,
            row_label=ascii_uppercase[linha],
            number=numero,
            kind=(
                SeatKind.ACCESSIBLE
                if linha == 0 and numero <= 2
                else SeatKind.STANDARD
            ),
        )
        for linha in range(room.rows)
        for numero in range(1, room.seats_per_row + 1)
    ]

    db.add_all(seats)
    db.flush()
    return len(seats)


def has_seats(db: Session, showing_id: int) -> bool:
    return db.scalar(
        select(Seat.id).where(Seat.showing_id == showing_id).limit(1)
    ) is not None


def taken_seat_ids(db: Session, showing_id: int) -> set[int]:
    """Assentos com ingresso vivo: vendidos ou em checkout.

    Espera vencida não conta — o assento já voltou ao estoque, e considerá-lo
    ocupado esconderia poltrona livre do cliente.
    """
    agora = datetime.now(timezone.utc)

    linhas = db.scalars(
        select(Ticket.seat_id)
        .join(Seat, Ticket.seat_id == Seat.id)
        .where(
            Seat.showing_id == showing_id,
            Ticket.status != TicketStatus.CANCELLED,
            or_(
                Ticket.status != TicketStatus.HELD,
                Ticket.held_until > agora,
            ),
        )
    )
    return set(linhas)


def sold_count(db: Session, showing_id: int) -> int:
    """Ingressos vivos da exibição — reservados, válidos ou já utilizados."""
    return db.scalar(
        select(func.count(Ticket.id))
        .join(Seat, Ticket.seat_id == Seat.id)
        .where(
            Seat.showing_id == showing_id,
            Ticket.status != TicketStatus.CANCELLED,
        )
    ) or 0
