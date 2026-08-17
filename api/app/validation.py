"""Validação do ingresso na portaria.

Nenhum dos desfechos é erro de requisição: os quatro têm o mesmo posto, e
quem os lê é um operador com uma pessoa parada na frente esperando entrar.
Traduzir "inválido" em 404 faria a tela tratar metade dos casos como falha de
rede — e um ingresso recusado é resposta, não falha.

A ordem das perguntas é deliberada. Primeiro *qual evento*, depois *qual
estado*: descobrir tarde demais que o ingresso é da sala ao lado já teria
queimado um ingresso legítimo de outra portaria.
"""

import enum
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import (
    Event, Order, Room, Seat, Showing, Ticket, TicketStatus, User,
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
    WRONG_EVENT = "wrong_event"

    # Quinto estado, além dos quatro exigidos. Um ingresso reembolsado
    # apresentado na porta é situação real, e chamá-lo de "inválido" faria o
    # operador tratar como fraudador quem apenas cancelou e esqueceu. Mesma
    # razão que separa "outro evento" de "inválido".
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Validation:
    """O que a tela da portaria precisa mostrar, já resolvido."""

    result: GateResult

    seat_label: str | None = None
    customer_name: str | None = None
    room_name: str | None = None
    starts_at: datetime | None = None

    # Só em ALREADY_USED: sem o horário anterior o operador não tem como
    # saber se a entrada foi há um minuto ou na semana passada.
    used_at: datetime | None = None

    # Só em WRONG_EVENT: para qual evento o ingresso realmente vale.
    ticket_event_title: str | None = None


def _extrair_jti(codigo: str) -> tuple[str | None, int | None]:
    """Aceita o QR assinado ou o código impresso, e diz de onde veio.

    O segundo elemento é o evento que a assinatura afirma — `None` quando o
    código foi digitado, porque aí não há assinatura de onde tirá-lo.
    """
    codigo = codigo.strip()

    payload = decode_token(codigo, expected_type=TOKEN_TYPE_TICKET)
    if payload is not None:
        return payload.get("jti"), payload.get("evt")

    # Digitação manual, para quando a câmera não coopera. O que sustenta este
    # caminho não é assinatura, e sim o `jti` ser um uuid4 — 122 bits que não
    # se adivinham — somado ao papel de portaria exigido na rota (D17).
    try:
        return str(uuid.UUID(codigo)), None
    except ValueError:
        return None, None


def _carregar(db: Session, jti: str):
    """Ingresso e tudo que a tela mostra, numa consulta só."""
    return db.execute(
        select(Ticket, Seat, Showing, Event, Room, User)
        .join(Seat, Ticket.seat_id == Seat.id)
        .join(Showing, Seat.showing_id == Showing.id)
        .join(Event, Showing.event_id == Event.id)
        .join(Room, Showing.room_id == Room.id)
        .join(Order, Ticket.order_id == Order.id)
        .join(User, Order.customer_id == User.id)
        .where(Ticket.jti == jti)
    ).first()


def validate(db: Session, gate: User, codigo: str) -> Validation:
    if gate.gate_event_id is None:
        raise GateError(
            "Esta portaria não está vinculada a nenhum evento. "
            "Peça ao organizador para vinculá-la antes de validar."
        )

    jti, evento_do_token = _extrair_jti(codigo)
    if jti is None:
        return Validation(GateResult.INVALID)

    linha = _carregar(db, jti)
    if linha is None:
        return Validation(GateResult.INVALID)

    ticket, seat, showing, event, room, customer = linha

    # A assinatura afirma um evento. Se ela discorda do banco, o token foi
    # montado para apontar um ingresso que não é o dele.
    if evento_do_token is not None and evento_do_token != event.id:
        return Validation(GateResult.INVALID)

    if event.id != gate.gate_event_id:
        # Estado próprio, nunca "inválido": o ingresso é legítimo e quem está
        # na porta errada é a pessoa. Colapsar os dois mandaria embora alguém
        # que só precisa da sala ao lado.
        return Validation(
            GateResult.WRONG_EVENT,
            seat_label=seat.label,
            customer_name=customer.name,
            room_name=room.name,
            starts_at=showing.starts_at,
            ticket_event_title=event.title,
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
        room_name=room.name,
        starts_at=showing.starts_at,
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
