"""Reserva, pagamento e ingressos do cliente."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.booking import BookingError, hold_seats, pay
from app.cancellation import CancellationError, cancel_ticket
from app.deps import Customer, DbSession
from app.models import (
    Event, Order, Room, Seat, Showing, Ticket, TicketStatus, Venue,
)
from app.schemas import (
    MyTicketOut, OrderOut, PaymentIn, PaymentOut, ReservationIn, TicketOut,
)
from app.security import create_ticket_token

router = APIRouter(tags=["reserva e ingressos"])

# Quanto tempo o ingresso que o próprio cliente cancelou continua na lista.
# Curto de propósito: ele sabe por que cancelou, e o único papel da janela é
# não fazer o bilhete evaporar no mesmo instante do clique.
JANELA_CANCELADO_PELO_CLIENTE = timedelta(minutes=30)


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
    agora = datetime.now(timezone.utc)

    # O ingresso cancelado sai da lista, mas os dois cancelamentos têm prazos
    # diferentes porque servem a leitores diferentes: quem cancelou já sabe o
    # motivo, quem teve a sessão cancelada precisa lê-lo justamente perto da
    # data em que iria. Filtrar aqui e nunca apagar a linha — o ingresso é
    # registro de uma compra, e o índice parcial depende do status.
    ainda_listavel = or_(
        Ticket.status != TicketStatus.CANCELLED,
        and_(
            Showing.cancelled_at.is_not(None),
            Showing.starts_at > agora,
        ),
        and_(
            Showing.cancelled_at.is_(None),
            Ticket.cancelled_at > agora - JANELA_CANCELADO_PELO_CLIENTE,
        ),
    )

    linhas = db.execute(
        select(Ticket, Seat, Showing, Event, Room, Venue)
        .join(Seat, Ticket.seat_id == Seat.id)
        .join(Showing, Seat.showing_id == Showing.id)
        .join(Event, Showing.event_id == Event.id)
        .join(Room, Showing.room_id == Room.id)
        .join(Venue, Room.venue_id == Venue.id)
        .join(Order, Ticket.order_id == Order.id)
        # A reserva não paga nunca aparece: ela ainda não é um ingresso.
        .where(
            Order.customer_id == customer.id,
            Ticket.status != TicketStatus.HELD,
            ainda_listavel,
        )
        .order_by(Showing.starts_at)
    ).all()

    return [
        MyTicketOut(
            id=t.id,
            jti=t.jti,
            status=t.status,
            seat_label=seat.label,
            qr_token=create_ticket_token(t.jti, showing.id),
            event_title=event.title,
            poster_url=event.poster_url,
            venue_name=venue.name,
            venue_address=venue.address,
            venue_city=venue.city,
            room_name=room.name,
            starts_at=showing.starts_at,
            audio=showing.audio,
            price_cents=showing.price_cents,
            showing_cancelled=showing.cancelled_at is not None,
            cancellation_reason=showing.cancellation_reason,
        )
        for t, seat, showing, event, room, venue in linhas
    ]


@router.post(
    "/tickets/{ticket_id}/cancel",
    response_model=list[MyTicketOut],
    tags=["cliente"],
    summary="Cancela o próprio ingresso e devolve a poltrona ao estoque",
)
def cancel_my_ticket(
    ticket_id: int, db: DbSession, customer: Customer
) -> list[MyTicketOut]:
    ingresso = db.get(Ticket, ticket_id)
    dono = db.scalar(
        select(Order.customer_id).where(Order.id == ingresso.order_id)
    ) if ingresso else None

    if ingresso is None or dono != customer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingresso não encontrado.")

    try:
        cancel_ticket(db, ingresso)
    except CancellationError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, erro.message)

    return my_tickets(db, customer)
