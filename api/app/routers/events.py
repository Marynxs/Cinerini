"""Eventos e suas sessões, do rascunho à publicação.

Operações sobre uma sessão específica vivem em showings.py. Aqui ficam as
que são de fato do evento.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import DbSession, Organizer
from app.models import Event, EventStatus, Room, Showing, User
from app.catalog import listar, uma_sessao
from app.schemas import CatalogEventOut, EventIn, EventOut, ShowingIn, ShowingOut
from app.seating import generate_seats, has_seats
from app.tmdb import movie_details

router = APIRouter(prefix="/events", tags=["eventos"])


def _evento(db: DbSession, event_id: int) -> Event:
    """O evento, sem recorte por quem o criou.

    O catálogo é de uma operação só, não de cada organizador (D29):
    `organizer_id` registra quem publicou, e deixou de ser cerca de acesso.
    """
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")
    return event


@router.get("", response_model=list[CatalogEventOut])
def list_published(db: DbSession, city: int | None = None) -> list[CatalogEventOut]:
    """Catálogo público: filmes em cartaz com suas sessões futuras."""
    return listar(db, city)


@router.get("/managed", response_model=list[EventOut])
def list_managed(db: DbSession, _: Organizer) -> list[Event]:
    """Tudo que o painel administra, publicado ou não.

    Diferente de `GET /events`, que é o catálogo público e só mostra o que
    está publicado. Aqui entram os rascunhos, porque é onde eles são
    terminados.

    Sem filtro por quem criou: a equipe administra um catálogo só (D29).
    """
    return list(
        db.scalars(select(Event).order_by(Event.created_at.desc()))
    )


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: DbSession) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")
    return event


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(data: EventIn, db: DbSession, organizer: Organizer) -> Event:
    """O mesmo filme não entra duas vezes.

    Dois eventos do mesmo `tmdb_id` produziriam dois blocos idênticos no
    catálogo, com as sessões repartidas entre eles, e o cliente veria "Duna"
    duas vezes e teria de abrir os dois para saber onde está o horário que
    procura. Um filme é um evento, e as sessões se penduram nele (D30).
    """
    if data.tmdb_id is not None:
        repetido = db.scalar(
            select(Event).where(Event.tmdb_id == data.tmdb_id).limit(1))
        if repetido is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"'{repetido.title}' já está no catálogo. "
                "Crie as sessões no evento existente.",
            )
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


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: DbSession, _: Organizer) -> None:
    """Só rascunho, e só sem sessões.

    Publicado não sai porque pode ter ingresso vendido, e apagar levaria
    junto o comprovante de quem comprou. Rascunho com sessões também não:
    esvaziar antes torna a consequência visível passo a passo, em vez de
    escondê-la atrás de uma confirmação genérica (D30).

    Despublicar não é apagar: um evento que saiu do ar continua com o
    histórico dele, e é isso que o `unpublish` existe para fazer.
    """
    event = _evento(db, event_id)

    if event.status != EventStatus.DRAFT:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Só rascunhos podem ser removidos. Despublique o evento antes, "
            "e se ele já vendeu ingressos, despublicar é o mais longe que dá.",
        )

    com_sessao = db.scalar(
        select(Showing.id).where(Showing.event_id == event_id).limit(1))
    if com_sessao is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este rascunho tem sessões. Remova as sessões antes.",
        )

    db.delete(event)
    db.commit()


@router.post("/{event_id}/publish", response_model=EventOut)
def publish(event_id: int, db: DbSession, organizer: Organizer) -> Event:
    event = _evento(db, event_id)

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
    event = _evento(db, event_id)
    event.status = EventStatus.DRAFT
    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}/showings", response_model=list[ShowingOut])
def list_showings(event_id: int, db: DbSession) -> list[ShowingOut]:
    if db.get(Event, event_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")

    sessoes = db.scalars(
        select(Showing)
        .where(Showing.event_id == event_id)
        .order_by(Showing.starts_at)
    ).all()

    return [uma_sessao(db, s.id) for s in sessoes]


@router.post(
    "/{event_id}/showings",
    response_model=ShowingOut,
    status_code=status.HTTP_201_CREATED,
)
def create_showing(
    event_id: int, data: ShowingIn, db: DbSession, organizer: Organizer
) -> ShowingOut:
    event = _evento(db, event_id)

    if db.get(Room, data.room_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada.")

    showing = Showing(event_id=event.id, **data.model_dump())
    db.add(showing)
    db.flush()

    # Poltronas na criação, e não só na publicação. Adiar fazia a sessão
    # recém-criada de um rascunho anunciar ocupação 0/0, que não é "sala
    # vazia" e sim "sala inexistente": o painel mostrava o mesmo número para
    # uma sessão sem mapa e para uma sessão de sala vazia. Trocar a sala
    # segue livre enquanto ninguém comprou, porque o PATCH regenera o mapa (D9).
    generate_seats(db, showing)

    db.commit()
    db.refresh(showing)
    return uma_sessao(db, showing.id)
