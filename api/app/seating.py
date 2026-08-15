"""Geração do mapa de assentos de uma exibição."""

from string import ascii_uppercase

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Seat, SeatKind, Showing, Ticket, TicketStatus


def generate_seats(db: Session, showing: Showing) -> int:
    """Cria as poltronas a partir do layout da sala. Devolve quantas criou.

    Fileira A é a mais próxima da tela. As duas primeiras poltronas da última
    fileira são acessíveis: é onde o acesso é plano em sala inclinada, e é
    onde salas reais costumam reservá-las.
    """
    room = showing.room
    ultima_fileira = ascii_uppercase[room.rows - 1]

    seats = [
        Seat(
            showing_id=showing.id,
            row_label=ascii_uppercase[linha],
            number=numero,
            kind=(
                SeatKind.ACCESSIBLE
                if ascii_uppercase[linha] == ultima_fileira and numero <= 2
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
