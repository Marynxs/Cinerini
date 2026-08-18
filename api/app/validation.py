"""Validação do ingresso na portaria.

Nenhum dos desfechos é erro de requisição: todos têm o mesmo posto, e quem os
lê é um operador com uma pessoa parada na frente esperando entrar. Traduzir
"inválido" em 404 faria a tela tratar metade dos casos como falha de rede — e
um ingresso recusado é resposta, não falha.

A ordem das perguntas é deliberada. Primeiro *onde este ingresso vale*, depois
*se ainda vale*: descobrir tarde demais que o ingresso é da sessão seguinte já
teria queimado um ingresso legítimo de outra portaria.
"""

import enum
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import (
    Event, Order, Room, Seat, Showing, Ticket, TicketStatus, User, Venue,
)
from app.security import TOKEN_TYPE_TICKET, decode_token


class GateError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class GateResult(str, enum.Enum):
    VALID = "valid"
    INVALID = "invalid"
    ALREADY_USED = "already_used"

    # Filme diferente do que esta porta atende.
    WRONG_EVENT = "wrong_event"

    # Filme certo, exibição errada: outro horário, outra sala ou outro
    # cinema. Separado de WRONG_EVENT porque a reação de quem opera é
    # diferente — um manda para outra sala, o outro para outro horário, e às
    # vezes para outro dia (D21).
    WRONG_SHOWING = "wrong_showing"

    # Ingresso reembolsado apresentado na porta é situação real, e chamá-lo
    # de "inválido" faria o operador tratar como fraudador quem apenas
    # cancelou e esqueceu.
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Sessao:
    """Uma exibição, do jeito que a portaria precisa ler."""

    # Carregado para comparar filmes por identidade, e não por título: dois
    # eventos podem se chamar igual, e aí a portaria diria "outra sessão"
    # sobre um ingresso de outro filme.
    event_id: int

    event_title: str
    starts_at: datetime
    venue_name: str
    venue_city: str
    room_name: str


@dataclass(frozen=True)
class Validation:
    """O que a tela da portaria precisa mostrar, já resolvido."""

    result: GateResult

    seat_label: str | None = None
    customer_name: str | None = None

    # A exibição a que o ingresso pertence. Vem preenchida sempre que houve
    # ingresso de verdade — no desfecho válido para conferir, nos recusados
    # para dizer a quem foi barrado onde o ingresso vale.
    showing: Sessao | None = None

    # Só em ALREADY_USED: sem o horário anterior o operador não tem como
    # saber se a entrada foi há um minuto ou na semana passada.
    used_at: datetime | None = None


def _extrair_jti(codigo: str) -> tuple[str | None, int | None]:
    """Aceita o QR assinado ou o código impresso, e diz de onde veio.

    O segundo elemento é a exibição que a assinatura afirma — `None` quando o
    código foi digitado, porque aí não há assinatura de onde tirá-la.
    """
    codigo = codigo.strip()

    payload = decode_token(codigo, expected_type=TOKEN_TYPE_TICKET)
    if payload is not None:
        return payload.get("jti"), payload.get("shw")

    # Digitação manual, para quando a câmera não coopera. O que sustenta este
    # caminho não é assinatura, e sim o `jti` ser um uuid4 — 122 bits que não
    # se adivinham — somado ao papel de portaria exigido na rota (D16).
    try:
        return str(uuid.UUID(codigo)), None
    except ValueError:
        return None, None


def _carregar(db: Session, jti: str):
    """Ingresso e tudo que a tela mostra, numa consulta só."""
    return db.execute(
        select(Ticket, Seat, Showing, Event, Room, Venue, User)
        .join(Seat, Ticket.seat_id == Seat.id)
        .join(Showing, Seat.showing_id == Showing.id)
        .join(Event, Showing.event_id == Event.id)
        .join(Room, Showing.room_id == Room.id)
        .join(Venue, Room.venue_id == Venue.id)
        .join(Order, Ticket.order_id == Order.id)
        .join(User, Order.customer_id == User.id)
        .where(Ticket.jti == jti)
    ).first()


def describe(db: Session, showing_id: int) -> Sessao | None:
    """A exibição em uma linha, para a tela dizer a que porta atende."""
    linha = db.execute(
        select(Showing, Event, Room, Venue)
        .join(Event, Showing.event_id == Event.id)
        .join(Room, Showing.room_id == Room.id)
        .join(Venue, Room.venue_id == Venue.id)
        .where(Showing.id == showing_id)
    ).first()

    if linha is None:
        return None

    showing, event, room, venue = linha
    return Sessao(
        event_id=event.id,
        event_title=event.title,
        starts_at=showing.starts_at,
        venue_name=venue.name,
        venue_city=venue.city,
        room_name=room.name,
    )


def validate(db: Session, gate: User, codigo: str) -> Validation:
    if gate.gate_showing_id is None:
        raise GateError(
            "Nenhuma sessão escolhida para este turno. Escolha a sessão "
            "que você está atendendo antes de validar."
        )

    jti, sessao_do_token = _extrair_jti(codigo)
    if jti is None:
        return Validation(GateResult.INVALID)

    linha = _carregar(db, jti)
    if linha is None:
        return Validation(GateResult.INVALID)

    ticket, seat, showing, event, room, venue, customer = linha

    # A assinatura afirma uma exibição. Se ela discorda do banco, o token foi
    # montado para apontar um ingresso que não é o dele.
    if sessao_do_token is not None and sessao_do_token != showing.id:
        return Validation(GateResult.INVALID)

    sessao = Sessao(
        event_id=event.id,
        event_title=event.title,
        starts_at=showing.starts_at,
        venue_name=venue.name,
        venue_city=venue.city,
        room_name=room.name,
    )

    if showing.id != gate.gate_showing_id:
        # Duas recusas e não uma: quem errou o filme precisa saber que veio
        # ao lugar errado, quem errou o horário precisa saber que veio na
        # hora errada. Colapsar as duas num "inválido" mandaria embora, como
        # fraudador, quem tem ingresso legítimo na mão (garantia 4).
        atendida = describe(db, gate.gate_showing_id)
        mesmo_filme = atendida is not None and atendida.event_id == event.id

        return Validation(
            GateResult.WRONG_SHOWING if mesmo_filme else GateResult.WRONG_EVENT,
            seat_label=seat.label,
            customer_name=customer.name,
            showing=sessao,
        )

    agora = datetime.now(timezone.utc)

    # A decisão sobre "já utilizado" é esta escrita, e não uma leitura antes
    # dela: entre ler "válido" e gravar "usado" cabe o mesmo QR sendo lido de
    # novo. Só a contagem de linhas afetadas prova quem chegou primeiro.
    marcado = db.execute(
        update(Ticket)
        .where(Ticket.jti == jti, Ticket.status == TicketStatus.VALID)
        .values(status=TicketStatus.USED, used_at=agora, validated_by=gate.id)
        .returning(Ticket.id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()

    db.commit()

    comuns = dict(
        seat_label=seat.label,
        customer_name=customer.name,
        showing=sessao,
    )

    if marcado is not None:
        return Validation(GateResult.VALID, **comuns)

    # Zero linhas: o ingresso existe e não estava válido. Só agora relemos o
    # status, e apenas para explicar — a decisão já foi tomada acima.
    db.refresh(ticket)

    if ticket.status == TicketStatus.USED:
        return Validation(GateResult.ALREADY_USED, used_at=ticket.used_at, **comuns)

    if ticket.status == TicketStatus.CANCELLED:
        return Validation(GateResult.CANCELLED, **comuns)

    # Sobra HELD: reserva sem pagamento, para a qual nenhum QR foi emitido.
    return Validation(GateResult.INVALID)
