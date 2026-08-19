"""Montagem do catálogo público.

Fora dos handlers de rota porque a consulta cruza cinco tabelas e resolve
disponibilidade, e porque a mesma montagem serve à listagem e ao detalhe
de uma sessão.
"""

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Event, EventStatus, Room, Seat, Showing, Ticket, TicketStatus, Venue,
)
from app.schemas import CatalogEventOut, ShowingOut


def _ocupados_por_sessao(db: Session, showing_ids: list[int]) -> dict[int, int]:
    """Quantos assentos estão indisponíveis em cada sessão.

    Numa consulta só, e não uma por sessão: o catálogo lista dezenas de
    sessões, e uma consulta por linha seria o problema N+1.
    """
    if not showing_ids:
        return {}

    agora = datetime.now(timezone.utc)

    linhas = db.execute(
        select(Seat.showing_id, func.count(Ticket.id))
        .join(Ticket, Ticket.seat_id == Seat.id)
        .where(
            Seat.showing_id.in_(showing_ids),
            Ticket.status != TicketStatus.CANCELLED,
            or_(Ticket.status != TicketStatus.HELD, Ticket.held_until > agora),
        )
        .group_by(Seat.showing_id)
    ).all()

    return {showing_id: total for showing_id, total in linhas}


def _total_por_sessao(db: Session, showing_ids: list[int]) -> dict[int, int]:
    if not showing_ids:
        return {}

    linhas = db.execute(
        select(Seat.showing_id, func.count(Seat.id))
        .where(Seat.showing_id.in_(showing_ids))
        .group_by(Seat.showing_id)
    ).all()

    return {showing_id: total for showing_id, total in linhas}


def montar_sessao(
    showing: Showing, room: Room, venue: Venue, event: Event,
    disponiveis: int, total: int = 0,
) -> ShowingOut:
    return ShowingOut(
        id=showing.id,
        event_id=showing.event_id,
        room_id=showing.room_id,
        starts_at=showing.starts_at,
        audio=showing.audio,
        price_cents=showing.price_cents,
        venue_name=venue.name,
        venue_city=venue.city,
        venue_address=venue.address,
        room_name=room.name,
        seats_available=disponiveis,
        seats_total=total,
        cancelled_at=showing.cancelled_at,
        cancellation_reason=showing.cancellation_reason,
        event_title=event.title,
        poster_url=event.poster_url,
        runtime_minutes=event.runtime_minutes,
    )


def listar(db: Session, city: int | None = None) -> list[CatalogEventOut]:
    """Filmes em cartaz com suas sessões futuras.

    Sessão que já começou sai da lista: ninguém compra ingresso para algo
    que está passando.
    """
    agora = datetime.now(timezone.utc)

    stmt = (
        select(Showing, Room, Venue, Event)
        .join(Room, Showing.room_id == Room.id)
        .join(Venue, Room.venue_id == Venue.id)
        .join(Event, Showing.event_id == Event.id)
        .where(
            Event.status == EventStatus.PUBLISHED,
            Showing.starts_at > agora,
            Showing.cancelled_at.is_(None),
        )
        .order_by(Event.title, Showing.starts_at)
    )

    if city:
        stmt = stmt.where(Venue.city_ibge_id == city)

    linhas = db.execute(stmt).all()

    ids = [linha[0].id for linha in linhas]
    totais = _total_por_sessao(db, ids)
    ocupados = _ocupados_por_sessao(db, ids)

    catalogo: dict[int, CatalogEventOut] = {}

    for showing, room, venue, event in linhas:
        disponiveis = totais.get(showing.id, 0) - ocupados.get(showing.id, 0)

        if event.id not in catalogo:
            catalogo[event.id] = CatalogEventOut(
                id=event.id,
                title=event.title,
                synopsis=event.synopsis,
                poster_url=event.poster_url,
                backdrop_url=event.backdrop_url,
                runtime_minutes=event.runtime_minutes,
                showings=[],
            )

        catalogo[event.id].showings.append(
            montar_sessao(showing, room, venue, event, disponiveis,
                          totais.get(showing.id, 0))
        )

    return list(catalogo.values())


def uma_sessao(db: Session, showing_id: int) -> ShowingOut | None:
    linha = db.execute(
        select(Showing, Room, Venue, Event)
        .join(Room, Showing.room_id == Room.id)
        .join(Venue, Room.venue_id == Venue.id)
        .join(Event, Showing.event_id == Event.id)
        .where(Showing.id == showing_id)
    ).one_or_none()

    if linha is None:
        return None

    showing, room, venue, event = linha
    total = _total_por_sessao(db, [showing_id]).get(showing_id, 0)
    ocupado = _ocupados_por_sessao(db, [showing_id]).get(showing_id, 0)

    return montar_sessao(showing, room, venue, event, total - ocupado, total)
