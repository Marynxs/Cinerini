"""Cinemas e salas. Cadastro do organizador, leitura pública."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import DbSession, Organizer
from app.models import Room, Showing, Venue
from app.schemas import RoomIn, RoomOut, VenueIn, VenueOut

router = APIRouter(prefix="/venues", tags=["cinemas e salas"])


def _venue_or_404(db: DbSession, venue_id: int) -> Venue:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cinema não encontrado.")
    return venue


@router.get("", response_model=list[VenueOut])
def list_venues(db: DbSession, city: str | None = None) -> list[Venue]:
    stmt = select(Venue).order_by(Venue.city, Venue.name)
    if city:
        stmt = stmt.where(Venue.city.ilike(city))
    return list(db.scalars(stmt))


@router.get("/cities", response_model=list[str])
def list_cities(db: DbSession) -> list[str]:
    """Alimenta o filtro do catálogo, que começa pela cidade."""
    return list(db.scalars(select(Venue.city).distinct().order_by(Venue.city)))


@router.post("", response_model=VenueOut, status_code=status.HTTP_201_CREATED)
def create_venue(data: VenueIn, db: DbSession, _: Organizer) -> Venue:
    venue = Venue(**data.model_dump())
    db.add(venue)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Já existe um cinema com este nome nesta cidade.",
        )
    db.refresh(venue)
    return venue


@router.get("/{venue_id}/rooms", response_model=list[RoomOut])
def list_rooms(venue_id: int, db: DbSession) -> list[Room]:
    _venue_or_404(db, venue_id)
    return list(
        db.scalars(select(Room).where(Room.venue_id == venue_id).order_by(Room.name))
    )


@router.post(
    "/{venue_id}/rooms",
    response_model=RoomOut,
    status_code=status.HTTP_201_CREATED,
)
def create_room(venue_id: int, data: RoomIn, db: DbSession, _: Organizer) -> Room:
    _venue_or_404(db, venue_id)

    room = Room(venue_id=venue_id, **data.model_dump())
    db.add(room)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Já existe uma sala com este nome neste cinema.",
        )
    db.refresh(room)
    return room


@router.delete("/{venue_id}/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(venue_id: int, room_id: int, db: DbSession, _: Organizer) -> None:
    room = db.get(Room, room_id)
    if room is None or room.venue_id != venue_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada.")

    # Verificado aqui e não deixado para o RESTRICT do banco porque o erro
    # precisa dizer o motivo. O banco recusaria de qualquer forma.
    em_uso = db.scalar(select(Showing.id).where(Showing.room_id == room_id).limit(1))
    if em_uso is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta sala tem sessões agendadas e não pode ser removida.",
        )

    db.delete(room)
    db.commit()
