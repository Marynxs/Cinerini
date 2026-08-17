"""Portaria: valida o ingresso na entrada."""

from fastapi import APIRouter, HTTPException, status

from app.deps import DbSession, Gate
from app.models import Event
from app.schemas import ValidationIn, ValidationOut
from app.validation import GateError, validate

router = APIRouter(prefix="/gate", tags=["portaria"])


@router.get("/me", summary="Qual evento esta portaria valida")
def bound_event(db: DbSession, gate: Gate) -> dict:
    """A tela precisa nomear o evento antes de qualquer leitura.

    Sem isso o operador só descobre a qual porta está atendendo depois de
    recusar alguém por "outro evento".
    """
    evento = db.get(Event, gate.gate_event_id) if gate.gate_event_id else None

    return {
        "gate_name": gate.name,
        "event_id": evento.id if evento else None,
        "event_title": evento.title if evento else None,
    }


@router.post(
    "/validations",
    response_model=ValidationOut,
    summary="Lê o código do ingresso e devolve o estado da entrada",
)
def validate_ticket(
    data: ValidationIn, db: DbSession, gate: Gate
) -> ValidationOut:
    """Sempre 200: os desfechos são respostas de negócio, não falhas.

    O único erro de verdade é a portaria não estar vinculada a evento nenhum,
    que é configuração ausente e não veredito sobre o ingresso.
    """
    try:
        resultado = validate(db, gate, data.code)
    except GateError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, erro.message)

    return ValidationOut(
        result=resultado.result,
        seat_label=resultado.seat_label,
        customer_name=resultado.customer_name,
        room_name=resultado.room_name,
        starts_at=resultado.starts_at,
        used_at=resultado.used_at,
        ticket_event_title=resultado.ticket_event_title,
    )
