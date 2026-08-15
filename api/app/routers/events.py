"""Eventos e suas sessões, do rascunho à publicação.

Operações sobre uma sessão específica vivem em showings.py — aqui ficam as
que são de fato do evento.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import DbSession, Organizer
from app.models import Event, EventStatus, Room, Showing, User
from app.schemas import EventIn, EventOut, ShowingIn, ShowingOut
from app.seating import generate_seats, has_seats
from app.tmdb import movie_details

router = APIRouter(prefix="/events", tags=["eventos"])


def _owned_event(db: DbSession, event_id: int, organizer: User) -> Event:
    event = db.get(Event, event_id)
    # 404 e não 403 quando o dono é outro: responder "sem permissão"
    # confirmaria a existência, e o id é sequencial.
    if event is None or event.organizer_id != organizer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")
    return event


@router.get("", response_model=list[EventOut])
def list_published(db: DbSession) -> list[Event]:
    """Catálogo público: só o que está publicado."""
    return list(
        db.scalars(
            select(Event)
            .where(Event.status == EventStatus.PUBLISHED)
            .order_by(Event.title)
        )
    )


@router.get("/mine", response_model=list[EventOut])
def list_mine(db: DbSession, organizer: Organizer) -> list[Event]:
    return list(
        db.scalars(
            select(Event)
            .where(Event.organizer_id == organizer.id)
            .order_by(Event.created_at.desc())
        )
    )


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: DbSession) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")
    return event


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(data: EventIn, db: DbSession, organizer: Organizer) -> Event:
    if data.tmdb_id is not None:
        # A ficha vem do catálogo, não do corpo da requisição: aceitar título
        # e sinopse do cliente permitiria publicar um filme com dados que não
        # são os dele.
        event = Event(organizer_id=organizer.id, **movie_details(data.tmdb_id))
    else:
        if not data.title:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Informe um tmdb_id ou um título.",
            )
        event = Event(
            organizer_id=organizer.id,
            **data.model_dump(exclude={"tmdb_id"}),
        )

    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.post("/{event_id}/publish", response_model=EventOut)
def publish(event_id: int, db: DbSession, organizer: Organizer) -> Event:
    event = _owned_event(db, event_id, organizer)

    if not event.showings:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cadastre ao menos uma sessão antes de publicar.",
        )

    # Publicar é o gatilho da geração: enquanto é rascunho, o organizador
    # ainda troca a sala livremente porque não há mapa nem venda.
    for showing in event.showings:
        if not has_seats(db, showing.id):
            generate_seats(db, showing)

    event.status = EventStatus.PUBLISHED
    db.commit()
    db.refresh(event)
    return event


@router.post("/{event_id}/unpublish", response_model=EventOut)
def unpublish(event_id: int, db: DbSession, organizer: Organizer) -> Event:
    """Tira do catálogo sem apagar nada.

    Assentos e ingressos permanecem: quem comprou continua com ingresso
    válido e a portaria segue validando. Muda só a visibilidade.
    """
    event = _owned_event(db, event_id, organizer)
    event.status = EventStatus.DRAFT
    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}/showings", response_model=list[ShowingOut])
def list_showings(event_id: int, db: DbSession) -> list[Showing]:
    if db.get(Event, event_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")
    return list(
        db.scalars(
            select(Showing)
            .where(Showing.event_id == event_id)
            .order_by(Showing.starts_at)
        )
    )


@router.post(
    "/{event_id}/showings",
    response_model=ShowingOut,
    status_code=status.HTTP_201_CREATED,
)
def create_showing(
    event_id: int, data: ShowingIn, db: DbSession, organizer: Organizer
) -> Showing:
    event = _owned_event(db, event_id, organizer)

    if db.get(Room, data.room_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada.")

    showing = Showing(event_id=event.id, **data.model_dump())
    db.add(showing)
    db.flush()

    # Evento já publicado gera os assentos na hora: sessão nova num catálogo
    # no ar precisa estar comprável imediatamente.
    if event.status == EventStatus.PUBLISHED:
        generate_seats(db, showing)

    db.commit()
    db.refresh(showing)
    return showing
