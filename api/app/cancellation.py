"""Cancelamento de sessão e de ingresso, com reembolso simulado (D10).

Liberar os assentos não exige código: o índice único é parcial em
`status <> 'cancelled'`, então o ingresso cancelado sai do índice e a
poltrona volta ao estoque sozinha.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Order, OrderStatus, Seat, Showing, Ticket, TicketStatus,
)


class CancellationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def cancel_showing(db: Session, showing: Showing, reason: str) -> int:
    """Cancela a sessão e todos os ingressos dela. Devolve quantos cancelou.

    A sessão permanece no banco: quem tem ingresso precisa encontrar a
    explicação onde procuraria o ingresso, e não um vazio.
    """
    if showing.cancelled_at is not None:
        raise CancellationError("Esta sessão já foi cancelada.")

    ingressos = list(db.scalars(
        select(Ticket)
        .join(Seat, Ticket.seat_id == Seat.id)
        .where(
            Seat.showing_id == showing.id,
            Ticket.status.in_([TicketStatus.HELD, TicketStatus.VALID]),
        )
    ))

    agora = datetime.now(timezone.utc)

    for ingresso in ingressos:
        ingresso.status = TicketStatus.CANCELLED
        ingresso.held_until = None
        ingresso.cancelled_at = agora

    # Ingresso já utilizado não é revertido: a pessoa entrou, e apagar esse
    # fato falsificaria o histórico de quem passou pela portaria.

    pedidos = db.scalars(
        select(Order).where(
            Order.showing_id == showing.id,
            Order.status.in_([OrderStatus.PENDING, OrderStatus.PAID,
                              OrderStatus.REFUSED]),
        )
    ).all()

    for pedido in pedidos:
        pedido.status = OrderStatus.CANCELLED

    showing.cancelled_at = agora
    showing.cancellation_reason = reason.strip()

    db.commit()
    return len(ingressos)


def cancel_ticket(db: Session, ticket: Ticket) -> None:
    """Cancelamento pelo próprio cliente, antes da sessão começar."""
    if ticket.status == TicketStatus.USED:
        raise CancellationError(
            "Este ingresso já foi utilizado na entrada e não pode ser "
            "cancelado."
        )

    if ticket.status == TicketStatus.CANCELLED:
        raise CancellationError("Este ingresso já está cancelado.")

    sessao = db.scalar(
        select(Showing)
        .join(Seat, Seat.showing_id == Showing.id)
        .where(Seat.id == ticket.seat_id)
    )

    if sessao and sessao.starts_at <= datetime.now(timezone.utc):
        # Depois de a sessão começar, devolver o assento ao estoque venderia
        # um lugar para quem não teria como usá-lo.
        raise CancellationError(
            "A sessão já começou e o ingresso não pode mais ser cancelado."
        )

    ticket.status = TicketStatus.CANCELLED
    ticket.held_until = None
    ticket.cancelled_at = datetime.now(timezone.utc)

    # O pedido só é cancelado quando não sobra nenhum ingresso vivo: uma
    # compra de três poltronas com uma devolvida continua sendo uma compra.
    vivos = db.scalar(
        select(Ticket).where(
            Ticket.order_id == ticket.order_id,
            Ticket.status != TicketStatus.CANCELLED,
        ).limit(1)
    )

    if vivos is None:
        pedido = db.get(Order, ticket.order_id)
        if pedido is not None:
            pedido.status = OrderStatus.CANCELLED

    db.commit()
