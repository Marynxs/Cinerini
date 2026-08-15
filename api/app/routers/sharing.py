"""Compartilhamento de ingresso por link.

O token do link é separado da assinatura do ingresso de propósito: revogar
um compartilhamento não pode invalidar o ingresso, e são coisas com ciclos
de vida diferentes. Um mesmo ingresso pode ter vários links, revogados
individualmente.
"""

import secrets

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import Customer, DbSession
from app.models import (
    Event, Order, Room, Seat, ShareLink, Showing, Ticket, TicketStatus, Venue,
)
from app.schemas import ShareLinkOut, SharedTicketOut
from app.security import create_ticket_token

router = APIRouter(tags=["compartilhamento"])

# 32 bytes aleatórios em base64: inadivinhável por tentativa e ainda curto
# o bastante para caber numa URL sem ficar monstruoso.
TOKEN_BYTES = 32


def _meu_ingresso(db: DbSession, ticket_id: int, customer_id: int) -> Ticket:
    ingresso = db.get(Ticket, ticket_id)
    if ingresso is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingresso não encontrado.")

    dono = db.scalar(
        select(Order.customer_id).where(Order.id == ingresso.order_id)
    )
    if dono != customer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingresso não encontrado.")

    return ingresso


@router.post(
    "/tickets/{ticket_id}/share",
    response_model=ShareLinkOut,
    status_code=status.HTTP_201_CREATED,
    summary="Gera um link para o ingresso",
)
def create_share_link(
    ticket_id: int, db: DbSession, customer: Customer
) -> ShareLink:
    ingresso = _meu_ingresso(db, ticket_id, customer.id)

    if ingresso.status == TicketStatus.CANCELLED:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este ingresso foi cancelado e não pode ser compartilhado.",
        )

    link = ShareLink(ticket_id=ingresso.id,
                     token=secrets.token_urlsafe(TOKEN_BYTES))
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.get(
    "/tickets/{ticket_id}/share",
    response_model=list[ShareLinkOut],
    summary="Links já gerados para o ingresso",
)
def list_share_links(
    ticket_id: int, db: DbSession, customer: Customer
) -> list[ShareLink]:
    _meu_ingresso(db, ticket_id, customer.id)
    return list(db.scalars(
        select(ShareLink).where(ShareLink.ticket_id == ticket_id)
        .order_by(ShareLink.created_at.desc())
    ))


@router.delete(
    "/share/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoga um link sem afetar o ingresso",
)
def revoke(token: str, db: DbSession, customer: Customer) -> None:
    link = db.scalar(select(ShareLink).where(ShareLink.token == token))
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link não encontrado.")

    _meu_ingresso(db, link.ticket_id, customer.id)

    # Marcado, não apagado: um link removido devolveria "não encontrado",
    # indistinguível de endereço digitado errado. Revogado permite dizer que
    # o link existiu e foi desativado.
    link.revoked = True
    db.commit()


@router.get(
    "/share/{token}",
    response_model=SharedTicketOut,
    summary="Abre o ingresso compartilhado",
)
def open_shared(token: str, db: DbSession) -> SharedTicketOut:
    """Público: quem tem o link vê o ingresso, sem precisar de conta."""
    link = db.scalar(select(ShareLink).where(ShareLink.token == token))

    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link não encontrado.")

    if link.revoked:
        raise HTTPException(
            status.HTTP_410_GONE,
            "Este link foi desativado por quem compartilhou.",
        )

    linha = db.execute(
        select(Ticket, Seat, Showing, Event, Room, Venue)
        .join(Seat, Ticket.seat_id == Seat.id)
        .join(Showing, Seat.showing_id == Showing.id)
        .join(Event, Showing.event_id == Event.id)
        .join(Room, Showing.room_id == Room.id)
        .join(Venue, Room.venue_id == Venue.id)
        .where(Ticket.id == link.ticket_id)
    ).one_or_none()

    if linha is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingresso não encontrado.")

    ingresso, assento, sessao, evento, sala, cinema = linha

    return SharedTicketOut(
        status=ingresso.status,
        seat_label=assento.label,
        qr_token=create_ticket_token(ingresso.jti, evento.id),
        event_title=evento.title,
        poster_url=evento.poster_url,
        venue_name=cinema.name,
        room_name=sala.name,
        starts_at=sessao.starts_at,
        audio=sessao.audio,
    )
