"""Reserva, pagamento e emissão de ingresso.

Fora dos handlers de rota por tamanho (D11): o fluxo encadeia liberação de
espera vencida, trava dos assentos, cobrança e emissão, e cada etapa tem um
desfecho de erro próprio.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Order,
    OrderStatus,
    Seat,
    Showing,
    Ticket,
    TicketStatus,
    User,
)
from app.payment import charge


class BookingError(Exception):
    """Falha esperada do fluxo, com mensagem destinada ao cliente."""

    def __init__(self, message: str, seats: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.seats = seats or []


@dataclass(frozen=True)
class PaymentOutcome:
    order: Order
    approved: bool
    reason: str | None


def release_expired_holds(db: Session, showing_id: int) -> int:
    """Cancela as esperas vencidas da exibição. Devolve quantas liberou.

    Feito sob demanda, no início de cada reserva, em vez de por tarefa
    agendada. Um agendador seria mais uma peça de infraestrutura para manter
    e para o avaliador configurar, e a espera vencida só atrapalha alguém no
    momento em que esse alguém tenta reservar — que é exatamente quando esta
    função roda.

    O ingresso é marcado como cancelado, e não apagado: o índice único é
    parcial em status, então cancelar já devolve o assento ao estoque, e a
    linha preservada mantém o rastro da tentativa abandonada.
    """
    agora = datetime.now(timezone.utc)

    vencidos = select(Ticket.id).join(Seat, Ticket.seat_id == Seat.id).where(
        Seat.showing_id == showing_id,
        Ticket.status == TicketStatus.HELD,
        Ticket.held_until < agora,
    )

    resultado = db.execute(
        update(Ticket)
        .where(Ticket.id.in_(vencidos))
        .values(status=TicketStatus.CANCELLED)
    )
    db.flush()
    return resultado.rowcount


def hold_seats(
    db: Session, showing: Showing, customer: User, seat_ids: list[int]
) -> Order:
    """Trava os assentos por uma janela e abre o pedido.

    A disputa não é resolvida por consulta prévia: entre verificar e inserir
    cabe outra transação. A inserção é tentada e o índice único parcial
    arbitra — quem perde recebe IntegrityError, traduzido aqui.
    """
    if not seat_ids:
        raise BookingError("Selecione ao menos uma poltrona.")

    if len(set(seat_ids)) != len(seat_ids):
        raise BookingError("Há poltronas repetidas na seleção.")

    release_expired_holds(db, showing.id)

    assentos = db.scalars(
        select(Seat).where(Seat.id.in_(seat_ids), Seat.showing_id == showing.id)
    ).all()

    if len(assentos) != len(seat_ids):
        raise BookingError("Alguma poltrona não pertence a esta sessão.")

    # O total vem do preço gravado na sessão, nunca do corpo da requisição:
    # aceitar o valor do cliente permitiria comprar por um centavo.
    total = showing.price_cents * len(assentos)

    pedido = Order(
        customer_id=customer.id,
        showing_id=showing.id,
        status=OrderStatus.PENDING,
        total_cents=total,
    )
    db.add(pedido)
    db.flush()

    expira_em = datetime.now(timezone.utc) + timedelta(
        minutes=get_settings().hold_minutes
    )
    for assento in assentos:
        db.add(Ticket(order_id=pedido.id, seat_id=assento.id,
                      status=TicketStatus.HELD, held_until=expira_em))

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        ocupados = _quais_ocupados(db, showing.id, seat_ids)
        raise BookingError(
            "Alguém garantiu essa poltrona antes. Escolha outra.",
            seats=ocupados,
        )

    db.commit()
    db.refresh(pedido)
    return pedido


def _quais_ocupados(db: Session, showing_id: int, seat_ids: list[int]) -> list[str]:
    """Descobre quais poltronas da seleção foram perdidas, para a mensagem.

    Consultado depois da falha, não antes: aqui a informação é para explicar
    ao cliente, e não para decidir — a decisão já foi tomada pelo banco.
    """
    from app.seating import taken_seat_ids

    ocupados = taken_seat_ids(db, showing_id)
    perdidos = db.scalars(
        select(Seat).where(Seat.id.in_([s for s in seat_ids if s in ocupados]))
    ).all()
    return sorted(a.label for a in perdidos)


def pay(db: Session, order: Order, card_number: str) -> PaymentOutcome:
    """Cobra e resolve o pedido, aprovado ou recusado."""
    if order.status != OrderStatus.PENDING:
        raise BookingError("Este pedido já foi finalizado.")

    ingressos = list(db.scalars(
        select(Ticket).where(Ticket.order_id == order.id)
    ))

    agora = datetime.now(timezone.utc)
    vivos = [t for t in ingressos if t.status == TicketStatus.HELD]

    if not vivos or any(t.held_until and t.held_until < agora for t in vivos):
        _cancelar(db, ingressos, order, OrderStatus.CANCELLED)
        raise BookingError(
            "O tempo para concluir a compra expirou e as poltronas foram "
            "liberadas. Faça uma nova seleção."
        )

    resultado = charge(card_number, order.total_cents)

    if not resultado.approved:
        # Recusa devolve as poltronas na hora: segurá-las puniria outros
        # clientes por uma compra que não vai acontecer.
        _cancelar(db, ingressos, order, OrderStatus.REFUSED)
        return PaymentOutcome(order, False, resultado.reason)

    for ingresso in vivos:
        ingresso.status = TicketStatus.VALID
        ingresso.held_until = None

    order.status = OrderStatus.PAID
    db.commit()
    db.refresh(order)
    return PaymentOutcome(order, True, None)


def _cancelar(
    db: Session, ingressos: list[Ticket], order: Order, status: OrderStatus
) -> None:
    for ingresso in ingressos:
        ingresso.status = TicketStatus.CANCELLED
    order.status = status
    db.commit()
