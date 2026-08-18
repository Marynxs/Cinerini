"""Portaria: valida o ingresso na entrada.

Três responsabilidades separadas de propósito (D24):

- o **organizador** cria a conta e define em que cinema ela vale;
- o **funcionário** escolhe, a cada turno, qual sessão está atendendo;
- ninguém mais chega perto — o papel decide quem entra na sala.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import DbSession, Gate, Organizer
from app.models import Event, Role, Room, Showing, Ticket, User, Venue
from app.schemas import (
    CoverageOut, GateIn, GateOut, GateShiftIn, GateUpdate, ShowingBriefOut,
    ValidationIn, ValidationOut,
)
from app.security import hash_password
from app.validation import GateError, describe, validate

router = APIRouter(tags=["portaria"])

# Quanto do calendário o funcionário enxerga ao escolher o turno. Passado
# recente porque a sessão que começou há pouco ainda tem gente entrando;
# futuro curto porque uma lista com o mês inteiro esconderia a de hoje.
JANELA_ATRAS = timedelta(hours=4)
JANELA_ADIANTE = timedelta(days=2)


def _as_gate_out(db: Session, user: User) -> GateOut:
    cinema = db.get(Venue, user.gate_venue_id) if user.gate_venue_id else None

    return GateOut(
        id=user.id,
        name=user.name,
        email=user.email,
        venue_id=user.gate_venue_id,
        venue_name=cinema.name if cinema else None,
        showing_id=user.gate_showing_id,
        showing=describe(db, user.gate_showing_id) if user.gate_showing_id else None,
    )


def _sessoes_do_cinema(db: Session, venue_id: int) -> list[ShowingBriefOut]:
    agora = datetime.now(timezone.utc)

    linhas = db.execute(
        select(Showing, Event, Room, Venue)
        .join(Event, Showing.event_id == Event.id)
        .join(Room, Showing.room_id == Room.id)
        .join(Venue, Room.venue_id == Venue.id)
        .where(
            Venue.id == venue_id,
            # Sessão cancelada não recebe ninguém, então não entra na lista
            # de turnos possíveis.
            Showing.cancelled_at.is_(None),
            Showing.starts_at > agora - JANELA_ATRAS,
            Showing.starts_at < agora + JANELA_ADIANTE,
        )
        .order_by(Showing.starts_at)
    ).all()

    return [
        ShowingBriefOut(
            event_id=event.id,
            event_title=event.title,
            starts_at=showing.starts_at,
            venue_name=venue.name,
            venue_city=venue.city,
            room_name=room.name,
            showing_id=showing.id,
        )
        for showing, event, room, venue in linhas
    ]


def _funcionario(db: Session, gate_id: int) -> User:
    """A conta existe e é de funcionário.

    Sem recorte por organizador, e isso é consequência declarada de `Venue`
    não ter dono (D22): qualquer organizador já cadastra cinema e cria sala
    em cinema alheio, então recortar só a equipe seria uma cerca isolada em
    volta de um terreno aberto — daria a impressão de isolamento que o resto
    do cadastro não sustenta.

    A tentativa anterior recortava por "cinemas onde tenho sessão", e
    quebrava no caso mais comum: cinema recém-criado, funcionário
    cadastrado, nenhuma sessão marcada ainda — e o cadastro nascia
    impossível de corrigir. Fechar isso de verdade é dar dono ao `Venue`.
    """
    porteiro = db.get(User, gate_id)
    if porteiro is None or porteiro.role != Role.GATE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Funcionário não encontrado.")

    return porteiro


# ---------------------------------------------------------- quem valida


@router.get("/gate/me", response_model=GateOut,
            summary="Onde trabalho e o que estou atendendo")
def bound_showing(db: DbSession, gate: Gate) -> GateOut:
    return _as_gate_out(db, gate)


@router.get(
    "/gate/showings",
    response_model=list[ShowingBriefOut],
    summary="Sessões que posso atender neste cinema",
)
def my_showings(db: DbSession, gate: Gate) -> list[ShowingBriefOut]:
    """Só as do cinema onde a conta trabalha.

    É o escopo que impede alguém da portaria de um cinema validar ingresso de
    outro — e ele vem da conta, não da escolha de quem opera.
    """
    if gate.gate_venue_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta conta de portaria não está ligada a nenhum cinema. "
            "Peça ao organizador para corrigir o cadastro.",
        )

    return _sessoes_do_cinema(db, gate.gate_venue_id)


@router.put("/gate/shift", response_model=GateOut,
            summary="Escolhe a sessão do turno")
def choose_shift(data: GateShiftIn, db: DbSession, gate: Gate) -> GateOut:
    """Quem escolhe o turno é quem trabalha.

    O organizador não precisa estar por perto na virada de uma sessão para a
    seguinte — reapontar cada porta a cada duas horas não sobrevive a uma
    noite de operação real (D24).

    A liberdade é escolher *entre as sessões do próprio cinema*, e a lista é
    filtrada no servidor: mandar um id de fora não adianta.
    """
    if data.showing_id is None:
        gate.gate_showing_id = None
        db.commit()
        db.refresh(gate)
        return _as_gate_out(db, gate)

    if gate.gate_venue_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta conta de portaria não está ligada a nenhum cinema.",
        )

    permitidas = {s.showing_id for s in _sessoes_do_cinema(db, gate.gate_venue_id)}
    if data.showing_id not in permitidas:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Sessão indisponível para esta portaria.")

    gate.gate_showing_id = data.showing_id
    db.commit()
    db.refresh(gate)

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

    O único erro de verdade é não haver turno escolhido, que é configuração
    ausente e não veredito sobre o ingresso.
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
    summary="Contas de portaria dos cinemas onde este organizador tem sessões",
)
def my_gates(db: DbSession, _: Organizer) -> list[GateOut]:
    """Todos os funcionários, inclusive os sem cinema.

    Sem recorte por organizador pela mesma razão de `_funcionario`: `Venue`
    não tem dono, e a listagem precisa concordar com o que a edição permite.
    Os sem cinema entram porque são justamente os que precisam de atenção —
    escondê-los sumiria com o cadastro que ficou pela metade.
    """
    porteiros = db.scalars(
        select(User).where(User.role == Role.GATE).order_by(User.name)
    ).all()

    return [_as_gate_out(db, p) for p in porteiros]


@router.post(
    "/venues/{venue_id}/gates",
    response_model=GateOut,
    status_code=status.HTTP_201_CREATED,
    tags=["organizador"],
    summary="Cria uma conta de portaria para este cinema",
)
def create_gate(
    venue_id: int, data: GateIn, db: DbSession, organizer: Organizer
) -> GateOut:
    """Portaria não se auto-cadastra.

    O papel decide quem entra na sala, então quem o concede é o organizador —
    nunca o formulário público, que aceitaria qualquer visitante se
    declarando portaria.

    A conta é de uma pessoa e dura enquanto ela trabalhar ali. Uma por sessão
    encheria o sistema de contas mortas e obrigaria a distribuir senha nova a
    cada exibição (D24).
    """
    if db.get(Venue, venue_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cinema não encontrado.")

    if db.scalar(select(User).where(User.email == data.email)) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Já existe uma conta com este e-mail.")

    porteiro = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=Role.GATE,
        gate_venue_id=venue_id,
    )
    db.add(porteiro)
    db.commit()
    db.refresh(porteiro)

    return _as_gate_out(db, porteiro)


@router.patch(
    "/gates/{gate_id}",
    response_model=GateOut,
    tags=["organizador"],
    summary="Corrige o nome ou o cinema de um funcionário",
)
def update_gate(
    gate_id: int, data: GateUpdate, db: DbSession, organizer: Organizer
) -> GateOut:
    """Nome e cinema, nunca a senha.

    Trocar a senha pelo painel obrigaria a entregar a nova por algum canal, e
    o projeto evita exatamente isso (D22). Quem esquecer a senha precisa de
    uma conta nova — recuperação por e-mail está fora de escopo.
    """
    porteiro = _funcionario(db, gate_id)
    campos = data.model_dump(exclude_unset=True)

    if "name" in campos and campos["name"]:
        porteiro.name = campos["name"]

    if "venue_id" in campos:
        novo = campos["venue_id"]
        if novo is not None and db.get(Venue, novo) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cinema não encontrado.")

        # Mudar de cinema encerra o turno: a sessão que estava sendo atendida
        # é de outro lugar, e mantê-la deixaria a conta validando ingresso de
        # um cinema onde a pessoa não trabalha mais.
        if novo != porteiro.gate_venue_id:
            porteiro.gate_showing_id = None
        porteiro.gate_venue_id = novo

    db.commit()
    db.refresh(porteiro)
    return _as_gate_out(db, porteiro)


@router.delete(
    "/gates/{gate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["organizador"],
    summary="Remove uma conta de funcionário",
)
def delete_gate(gate_id: int, db: DbSession, organizer: Organizer) -> None:
    """Só sai quem nunca validou nada.

    `tickets.validated_by` aponta para quem estava na porta. Apagar a conta
    exigiria zerar esse campo, e o histórico deixaria de dizer quem deixou
    cada pessoa entrar — que é metade do motivo de a conta ser de gente e
    não de posto (D24).
    """
    porteiro = _funcionario(db, gate_id)

    validou = db.scalar(
        select(Ticket.id).where(Ticket.validated_by == gate_id).limit(1))
    if validou is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este funcionário já validou ingressos e não pode ser removido: "
            "o histórico da entrada deixaria de dizer quem estava na porta. "
            "Tire o cinema dele para que pare de validar.",
        )

    db.delete(porteiro)
    db.commit()


@router.get(
    "/gates/coverage",
    response_model=list[CoverageOut],
    tags=["organizador"],
    summary="Quem está na porta de cada sessão que começa em breve",
)
def coverage(db: DbSession, organizer: Organizer) -> list[CoverageOut]:
    """Vira a pergunta do avesso.

    A tabela de equipe responde "o que o João está atendendo?". Quem opera um
    cinema pergunta o contrário: "a sessão das 21:30 tem alguém na porta?".
    Sem esta lista, a resposta sai de cruzar duas colunas na cabeça — e o
    erro só aparece quando a fila já se formou (D26).

    A janela é a mesma da escolha de turno: o organizador enxerga exatamente
    as sessões que alguém pode assumir agora.

    Recortado pelos eventos deste organizador, que são os que têm dono de
    verdade no modelo.
    """
    agora = datetime.now(timezone.utc)

    linhas = db.execute(
        select(Showing, Event, Room, Venue)
        .join(Event, Showing.event_id == Event.id)
        .join(Room, Showing.room_id == Room.id)
        .join(Venue, Room.venue_id == Venue.id)
        .where(
            Event.organizer_id == organizer.id,
            Showing.cancelled_at.is_(None),
            # Mesma janela que o funcionário enxerga ao escolher o turno.
            # Duas listas com prazos diferentes divergiriam: o organizador
            # veria uma sessão descoberta que ninguém consegue assumir, ou
            # deixaria de ver uma que já pode ser coberta.
            Showing.starts_at > agora - JANELA_ATRAS,
            Showing.starts_at < agora + JANELA_ADIANTE,
        )
        .order_by(Showing.starts_at)
    ).all()

    if not linhas:
        return []

    # Uma consulta para todos os turnos, e não uma por sessão: a lista é
    # curta, mas o padrão de uma consulta por linha é o que transforma tela
    # de painel em tela lenta.
    ids = [s.id for s, _, _, _ in linhas]
    porteiros: dict[int, list[str]] = {}
    for nome, sessao in db.execute(
        select(User.name, User.gate_showing_id)
        .where(User.role == Role.GATE, User.gate_showing_id.in_(ids))
        .order_by(User.name)
    ):
        porteiros.setdefault(sessao, []).append(nome)

    return [
        CoverageOut(
            showing=ShowingBriefOut(
                showing_id=showing.id,
                event_id=event.id,
                event_title=event.title,
                starts_at=showing.starts_at,
                venue_name=venue.name,
                venue_city=venue.city,
                room_name=room.name,
            ),
            staff=porteiros.get(showing.id, []),
        )
        for showing, event, room, venue in linhas
    ]
