"""Reserva, pagamento e ingressos do cliente."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.booking import BookingError, hold_seats, pay
from app.deps import Customer, DbSession
from app.models import (
    Event, Order, Room, Seat, Showing, Ticket, TicketStatus, Venue,
)
from app.schemas import (
    MyTicketOut, OrderOut, PaymentIn, PaymentOut, ReservationIn, TicketOut,
)
from app.security import create_ticket_token

router = APIRouter(tags=["reserva e ingressos"])


def _as_order_out(db: Session, order: Order) -> OrderOut:
    ingressos = db.scalars(
        select(Ticket).where(Ticket.order_id == order.id)
        .order_by(Ticket.id)
    ).all()

    return OrderOut(
        id=order.id,
        showing_id=order.showing_id,
        status=order.status,
        total_cents=order.total_cents,
        held_until=next((t.held_until for t in ingressos if t.held_until), None),
        tickets=[
            TicketOut(
                id=t.id, jti=t.jti, status=t.status,
                seat_id=t.seat_id, seat_label=t.seat.label,
                row_label=t.seat.row_label, number=t.seat.number,
            )
            for t in ingressos
        ],
    )


@router.post(
    "/showings/{showing_id}/reservations",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Trava as poltronas escolhidas e abre o pedido",
)
def reserve(
    showing_id: int, data: ReservationIn, db: DbSession, customer: Customer
) -> OrderOut:
    showing = db.get(Showing, showing_id)
    if showing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada.")

    try:
        pedido = hold_seats(db, showing, customer, data.seat_ids)
    except BookingError as erro:
        # 409 e não 400: a requisição estava correta, o estado é que mudou
        # entre a escolha do cliente e a chegada dela aqui.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"message": erro.message, "seats": erro.seats},
        )

    return _as_order_out(db, pedido)


@router.post(
    "/orders/{order_id}/payment",
    response_model=PaymentOut,
    summary="Cobra o pedido e emite os ingressos",
)
def checkout(
    order_id: int, data: PaymentIn, db: DbSession, customer: Customer
) -> PaymentOut:
    order = db.get(Order, order_id)
    if order is None or order.customer_id != customer.id:
        # 404 mesmo quando o pedido existe mas é de outro cliente: confirmar
        # a existência exporia o volume de vendas a quem varrer ids.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado.")

    try:
        resultado = pay(db, order, data.card_number)
    except BookingError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, erro.message)

    return PaymentOut(
        approved=resultado.approved,
        reason=resultado.reason,
        order=_as_order_out(db, resultado.order),
    )


@router.get("/me/orders", response_model=list[OrderOut], tags=["cliente"])
def my_orders(db: DbSession, customer: Customer) -> list[OrderOut]:
    pedidos = db.scalars(
        select(Order).where(Order.customer_id == customer.id)
        .order_by(Order.created_at.desc())
    ).all()
    return [_as_order_out(db, p) for p in pedidos]


@router.get("/me/tickets", response_model=list[MyTicketOut], tags=["cliente"])
def my_tickets(db: DbSession, customer: Customer) -> list[MyTicketOut]:
    """Área de "Meus ingressos": tudo que a tela precisa numa consulta só."""
    linhas = db.execute(
        select(Ticket, Seat, Showing, Event, Room, Venue)
        .join(Seat, Ticket.seat_id == Seat.id)
        .join(Showing, Seat.showing_id == Showing.id)
        .join(Event, Showing.event_id == Event.id)
        .join(Room, Showing.room_id == Room.id)
        .join(Venue, Room.venue_id == Venue.id)
        .join(Order, Ticket.order_id == Order.id)
        .where(
            Order.customer_id == customer.id,
            Ticket.status != TicketStatus.HELD,
            Ticket.status != TicketStatus.CANCELLED,
        )
        .order_by(Showing.starts_at)
    ).all()

    return [
        MyTicketOut(
            id=t.id,
            jti=t.jti,
            status=t.status,
            seat_label=seat.label,
            qr_token=create_ticket_token(t.jti, event.id),
            event_title=event.title,
            poster_url=event.poster_url,
            venue_name=venue.name,
            room_name=room.name,
            starts_at=showing.starts_at,
            audio=showing.audio,
            price_cents=showing.price_cents,
        )
        for t, seat, showing, event, room, venue in linhas
    ]
