"""Operações sobre uma sessão específica.

Separado de events.py porque estas rotas identificam a sessão diretamente,
sem passar pelo evento. Criar e listar sessões continua sob /events/{id},
que é onde o evento importa.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select

from app.deps import DbSession, Organizer
from app.models import Event, Room, Seat, Showing, User
from app.schemas import SeatOut, ShowingOut, ShowingUpdate
from app.seating import generate_seats, sold_count

router = APIRouter(prefix="/showings", tags=["sessões"])


def _showing_or_404(db: DbSession, showing_id: int) -> Showing:
    showing = db.get(Showing, showing_id)
    if showing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada.")
    return showing


def _owned(db: DbSession, showing: Showing, organizer: User) -> None:
    event = db.get(Event, showing.event_id)
    if event is None or event.organizer_id != organizer.id:
        # 404 e não 403: confirmar a existência permitiria mapear o catálogo
        # alheio varrendo ids sequenciais.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada.")


@router.get("/{showing_id}", response_model=ShowingOut)
def get_showing(showing_id: int, db: DbSession) -> Showing:
    return _showing_or_404(db, showing_id)


@router.get("/{showing_id}/seats", response_model=list[SeatOut])
def list_seats(showing_id: int, db: DbSession) -> list[Seat]:
    _showing_or_404(db, showing_id)
    return list(
        db.scalars(
            select(Seat)
            .where(Seat.showing_id == showing_id)
            .order_by(Seat.row_label, Seat.number)
        )
    )


@router.patch("/{showing_id}", response_model=ShowingOut)
def update_showing(
    showing_id: int, data: ShowingUpdate, db: DbSession, organizer: Organizer
) -> Showing:
    showing = _showing_or_404(db, showing_id)
    _owned(db, showing, organizer)

    campos = data.model_dump(exclude_unset=True)
    nova_sala = campos.pop("room_id", None)

    if nova_sala is not None and nova_sala != showing.room_id:
        if db.get(Room, nova_sala) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada.")

        # Decisão D9: com ingresso vendido, trocar a sala deixaria o mapa
        # descrevendo uma sala que não é a da sessão — o cliente teria
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
    return showing


@router.delete("/{showing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_showing(showing_id: int, db: DbSession, organizer: Organizer) -> None:
    showing = _showing_or_404(db, showing_id)
    _owned(db, showing, organizer)

    if sold_count(db, showing.id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta sessão já tem ingressos e não pode ser removida.",
        )

    db.delete(showing)
    db.commit()
