"""Portaria: valida o ingresso na entrada, e é cadastrada pelo organizador.

As duas metades vivem juntas porque tratam do mesmo recurso visto de dois
lados — quem opera a porta e quem a monta antes da sessão começar.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import DbSession, Gate, Organizer
from app.models import Event, Role, Showing, User
from app.schemas import (
    GateIn, GateOut, GateRebindIn, ValidationIn, ValidationOut,
)
from app.security import hash_password
from app.validation import GateError, describe, validate

router = APIRouter(tags=["portaria"])


def _as_gate_out(db: Session, user: User) -> GateOut:
    return GateOut(
        id=user.id,
        name=user.name,
        email=user.email,
        showing_id=user.gate_showing_id,
        showing=describe(db, user.gate_showing_id) if user.gate_showing_id else None,
    )


def _sessao_do_organizador(db: Session, showing_id: int, dono: User) -> Showing:
    """A sessão precisa existir e ser de um evento deste organizador.

    Sem a segunda checagem, qualquer organizador montaria portaria na sessão
    de outro — e portaria é quem decide quem entra.
    """
    sessao = db.get(Showing, showing_id)
    evento = db.get(Event, sessao.event_id) if sessao else None

    if sessao is None or evento is None or evento.organizer_id != dono.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada.")

    return sessao


# ---------------------------------------------------------- quem valida


@router.get("/gate/me", response_model=GateOut, summary="Que sessão esta portaria atende")
def bound_showing(db: DbSession, gate: Gate) -> GateOut:
    """A tela precisa nomear a sessão antes de qualquer leitura.

    Sem isso o operador só descobre a qual porta está atendendo depois de
    recusar alguém.
    """
    return _as_gate_out(db, gate)


@router.post(
    "/gate/validations",
    response_model=ValidationOut,
    summary="Lê o código do ingresso e devolve o estado da entrada",
)
def validate_ticket(
    data: ValidationIn, db: DbSession, gate: Gate
) -> ValidationOut:
    """Sempre 200: os desfechos são respostas de negócio, não falhas.

    O único erro de verdade é a portaria não estar vinculada a sessão
    nenhuma, que é configuração ausente e não veredito sobre o ingresso.
    """
    try:
        resultado = validate(db, gate, data.code)
    except GateError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, erro.message)

    return ValidationOut(
        result=resultado.result,
        seat_label=resultado.seat_label,
        customer_name=resultado.customer_name,
        showing=resultado.showing,
        used_at=resultado.used_at,
    )


# ------------------------------------------------------- quem cadastra


@router.get(
    "/gates",
    response_model=list[GateOut],
    tags=["organizador"],
    summary="Portarias das sessões deste organizador",
)
def my_gates(db: DbSession, organizer: Organizer) -> list[GateOut]:
    """Inclui as desvinculadas: são elas que precisam de atenção.

    A portaria sem sessão é a que sobrou da exibição de ontem, e some da
    lista justamente quando quem monta a próxima precisaria reaproveitá-la.
    """
    porteiros = db.scalars(
        select(User).where(User.role == Role.GATE).order_by(User.name)
    ).all()

    meus = {
        s.id for s in db.scalars(
            select(Showing)
            .join(Event, Showing.event_id == Event.id)
            .where(Event.organizer_id == organizer.id)
        )
    }

    return [
        _as_gate_out(db, p) for p in porteiros
        if p.gate_showing_id is None or p.gate_showing_id in meus
    ]


@router.post(
    "/showings/{showing_id}/gates",
    response_model=GateOut,
    status_code=status.HTTP_201_CREATED,
    tags=["organizador"],
    summary="Cria uma portaria para esta sessão",
)
def create_gate(
    showing_id: int, data: GateIn, db: DbSession, organizer: Organizer
) -> GateOut:
    """Portaria não se auto-cadastra.

    O papel decide quem entra na sala, então quem o concede é o organizador
    do evento — nunca o formulário público, que aceitaria qualquer visitante
    se declarando portaria.
    """
    sessao = _sessao_do_organizador(db, showing_id, organizer)

    if db.scalar(select(User).where(User.email == data.email)) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Já existe uma conta com este e-mail.")

    porteiro = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=Role.GATE,
        gate_showing_id=sessao.id,
    )
    db.add(porteiro)
    db.commit()
    db.refresh(porteiro)

    return _as_gate_out(db, porteiro)


@router.patch(
    "/gates/{gate_id}",
    response_model=GateOut,
    tags=["organizador"],
    summary="Aponta a portaria para outra sessão",
)
def rebind_gate(
    gate_id: int, data: GateRebindIn, db: DbSession, organizer: Organizer
) -> GateOut:
    """A mesma porta atende sessões diferentes ao longo do dia.

    Recadastrar uma conta por sessão encheria o sistema de porteiros mortos e
    obrigaria a distribuir uma senha nova a cada exibição.
    """
    porteiro = db.get(User, gate_id)
    if porteiro is None or porteiro.role != Role.GATE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Portaria não encontrada.")

    if porteiro.gate_showing_id is not None:
        # Só quem controla a sessão atual pode tirar a portaria dela.
        _sessao_do_organizador(db, porteiro.gate_showing_id, organizer)

    if data.showing_id is not None:
        _sessao_do_organizador(db, data.showing_id, organizer)

    porteiro.gate_showing_id = data.showing_id
    db.commit()
    db.refresh(porteiro)

    return _as_gate_out(db, porteiro)
