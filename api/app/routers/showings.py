"""Operações sobre uma sessão específica.

Separado de events.py porque estas rotas identificam a sessão diretamente,
sem passar pelo evento. Criar e listar sessões continua sob /events/{id},
que é onde o evento importa.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select

from app.deps import DbSession, Organizer
from app.models import (
    Event, Order, Room, Seat, ShareLink, Showing, Ticket, TicketStatus, User,
)
from app.cancellation import CancellationError, cancel_showing
from app.schemas import CancelIn, SeatOut, ShowingOut, ShowingUpdate
from app.catalog import uma_sessao
from app.seating import generate_seats, sold_count, taken_seat_ids

router = APIRouter(prefix="/showings", tags=["sessões"])


def _showing_or_404(db: DbSession, showing_id: int) -> Showing:
    showing = db.get(Showing, showing_id)
    if showing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada.")
    return showing


def _existe(db: DbSession, showing: Showing) -> None:
    """O evento da sessão precisa existir, e mais nada.

    A checagem de dono saiu: o catálogo é de uma operação só, e qualquer
    organizador opera qualquer sessão (D29). `organizer_id` continua no
    modelo como registro de quem publicou.
    """
    if db.get(Event, showing.event_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada.")


@router.get("/{showing_id}", response_model=ShowingOut)
def get_showing(showing_id: int, db: DbSession) -> ShowingOut:
    _showing_or_404(db, showing_id)
    return uma_sessao(db, showing_id)


@router.get("/{showing_id}/seats", response_model=list[SeatOut])
def list_seats(showing_id: int, db: DbSession) -> list[SeatOut]:
    """Mapa da sessão com a ocupação atual."""
    _showing_or_404(db, showing_id)

    assentos = db.scalars(
        select(Seat)
        .where(Seat.showing_id == showing_id)
        .order_by(Seat.row_label, Seat.number)
    ).all()

    ocupados = taken_seat_ids(db, showing_id)

    return [
        SeatOut(
            id=a.id, row_label=a.row_label, number=a.number, kind=a.kind,
            label=a.label, taken=a.id in ocupados,
        )
        for a in assentos
    ]


@router.patch("/{showing_id}", response_model=ShowingOut)
def update_showing(
    showing_id: int, data: ShowingUpdate, db: DbSession, organizer: Organizer
) -> ShowingOut:
    showing = _showing_or_404(db, showing_id)
    _existe(db, showing)

    campos = data.model_dump(exclude_unset=True)
    nova_sala = campos.pop("room_id", None)

    if nova_sala is not None and nova_sala != showing.room_id:
        if db.get(Room, nova_sala) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada.")

        # Decisão D9: com ingresso vendido, trocar a sala deixaria o mapa
        # descrevendo uma sala que não é a da sessão, e o cliente teria
        # comprado a F7 de uma sala que pode não ter fileira F.
        if sold_count(db, showing.id):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Esta sessão já tem ingressos e não pode mudar de sala. "
                "Cancele a sessão e crie outra.",
            )

        db.execute(delete(Seat).where(Seat.showing_id == showing.id))
        showing.room_id = nova_sala
        db.flush()
        db.refresh(showing)
        generate_seats(db, showing)

    for campo, valor in campos.items():
        setattr(showing, campo, valor)

    db.commit()
    db.refresh(showing)
    return uma_sessao(db, showing.id)


@router.post("/{showing_id}/cancel", response_model=ShowingOut)
def cancel(
    showing_id: int, data: CancelIn, db: DbSession, organizer: Organizer
) -> ShowingOut:
    """Cancela a sessão com motivo, devolvendo os assentos ao estoque (D10)."""
    showing = _showing_or_404(db, showing_id)
    _existe(db, showing)

    try:
        cancel_showing(db, showing, data.reason)
    except CancellationError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, erro.message)

    return uma_sessao(db, showing_id)


@router.delete("/{showing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_showing(showing_id: int, db: DbSession, organizer: Organizer) -> None:
    """Remove a sessão e tudo que só existia por causa dela.

    Duas recusas, e a diferença entre elas é o ponto. Ingresso já validado
    na portaria trava para sempre: alguém entrou naquela sessão, e apagar a
    linha falsificaria o histórico que a garantia 3 existe para manter.
    Ingresso ainda vivo trava até o cancelamento, que é o passo que diz o
    motivo a quem comprou e devolve o valor (D10). Só depois disso a sessão
    sai, levando poltronas, ingressos cancelados e pedidos.

    Descartado o botão único que apaga direto: a mesma confirmação estaria
    removendo um horário digitado errado e o ingresso que alguém pagou, e a
    tela não teria como mostrar que são coisas diferentes (D36).
    """
    showing = _showing_or_404(db, showing_id)
    _existe(db, showing)

    usados = db.scalar(
        select(func.count(Ticket.id))
        .join(Seat, Ticket.seat_id == Seat.id)
        .where(Seat.showing_id == showing_id,
               Ticket.status == TicketStatus.USED)
    ) or 0

    if usados:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{usados} ingresso(s) desta sessão já passaram pela portaria. "
            "A sessão aconteceu e não pode ser removida.",
        )

    vivos = sold_count(db, showing_id)

    if vivos:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Esta sessão tem {vivos} ingresso(s) ativo(s). Cancele a sessão "
            "antes: é o cancelamento que informa o motivo a quem comprou e "
            "devolve o valor.",
        )

    # Ordem inversa das dependências, porque nenhuma dessas chaves tem
    # cascata no banco: share_links aponta para tickets, tickets apontam
    # para seats e orders. As poltronas saem por cascata do ORM junto com a
    # sessão, e só sobrariam ingressos cancelados apontando para o vazio.
    ingressos = list(db.scalars(
        select(Ticket.id)
        .join(Seat, Ticket.seat_id == Seat.id)
        .where(Seat.showing_id == showing_id)
    ))

    if ingressos:
        db.execute(delete(ShareLink).where(ShareLink.ticket_id.in_(ingressos)))
        db.execute(delete(Ticket).where(Ticket.id.in_(ingressos)))

    db.execute(delete(Order).where(Order.showing_id == showing_id))

    db.delete(showing)
    db.commit()
