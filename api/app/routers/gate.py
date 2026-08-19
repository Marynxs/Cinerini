"""Portaria: valida o ingresso na entrada.

Três responsabilidades separadas de propósito (D24):

- o **organizador** cria a conta e define em que cinema ela vale;
- o **funcionário** escolhe, a cada turno, qual sessão está atendendo;
- ninguém mais chega perto: o papel decide quem entra na sala.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, true as sa_true
from sqlalchemy.orm import Session

from app.deps import DbSession, Gate, Organizer
from app.models import Event, Role, Room, Showing, Ticket, User, Venue
from app.schemas import (
    CoverageOut, CoverageStaffOut, GateIn, GateOut, GateShiftIn, GateUpdate,
    ShowingBriefOut, ValidationIn, ValidationOut,
)
from app.security import hash_password
from app.validation import GateError, describe, validate

router = APIRouter(tags=["portaria"])

# Quanto do calendário o funcionário enxerga ao escolher o turno. Passado
# recente porque a sessão que começou há pouco ainda tem gente entrando;
# futuro curto porque uma lista com o mês inteiro esconderia a de hoje.
JANELA_ATRAS = timedelta(hours=4)
# Três dias e não dois: a janela é contada a partir de agora, então
# "dois dias" desliza com a hora do dia e a sessão da noite de depois de
# amanhã caía fora conforme o relógio andava, presente no catálogo e
# ausente na lista de turnos.
JANELA_ADIANTE = timedelta(days=3)


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


def _sessoes_disponiveis(db: Session, quem: User) -> list[ShowingBriefOut]:
    """As sessões que esta conta pode assumir, e o recorte muda com o papel.

    Funcionário enxerga as do cinema onde trabalha: é o escopo do emprego, e
    é o que impede alguém do Belas Artes validar ingresso do Odeon.

    Organizador enxerga todas, em qualquer cinema: ele administra o catálogo
    inteiro (D29), e a portaria é mais uma coisa que ele pode fazer, não um
    emprego com escopo (D27).
    """
    agora = datetime.now(timezone.utc)

    escopo = (
        # `true` em vez de omitir a cláusula: mantém a forma da consulta e
        # deixa explícito que a ausência de recorte é decisão, não descuido.
        sa_true() if quem.role == Role.ORGANIZER
        else Venue.id == quem.gate_venue_id
    )

    linhas = db.execute(
        select(Showing, Event, Room, Venue)
        .join(Event, Showing.event_id == Event.id)
        .join(Room, Showing.room_id == Room.id)
        .join(Venue, Room.venue_id == Venue.id)
        .where(
            escopo,
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
    volta de um terreno aberto, dando a impressão de isolamento que o resto
    do cadastro não sustenta.

    A tentativa anterior recortava por "cinemas onde tenho sessão", e
    quebrava no caso mais comum: cinema recém-criado, funcionário
    cadastrado, nenhuma sessão marcada ainda, e o cadastro nascia
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
    outro, e ele vem da conta, não da escolha de quem opera.
    """
    if gate.role == Role.GATE and gate.gate_venue_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta conta de funcionário não está ligada a nenhum cinema. "
            "Peça ao organizador para corrigir o cadastro.",
        )

    return _sessoes_disponiveis(db, gate)


@router.put("/gate/shift", response_model=GateOut,
            summary="Escolhe a sessão do turno")
def choose_shift(data: GateShiftIn, db: DbSession, gate: Gate) -> GateOut:
    """Quem escolhe o turno é quem trabalha.

    O organizador não precisa estar por perto na virada de uma sessão para a
    seguinte, porque reapontar cada porta a cada duas horas não sobrevive a uma
    noite de operação real (D24).

    A liberdade é escolher *entre as sessões do próprio cinema*, e a lista é
    filtrada no servidor: mandar um id de fora não adianta.
    """
    if data.showing_id is None:
        gate.gate_showing_id = None
        db.commit()
        db.refresh(gate)
        return _as_gate_out(db, gate)

    if gate.role == Role.GATE and gate.gate_venue_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta conta de funcionário não está ligada a nenhum cinema.",
        )

    permitidas = {s.showing_id for s in _sessoes_disponiveis(db, gate)}
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
    Os sem cinema entram porque são justamente os que precisam de atenção:
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

    O papel decide quem entra na sala, então quem o concede é o organizador,
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
    uma conta nova, porque recuperação por e-mail está fora de escopo.
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

    if "showing_id" in campos:
        # O organizador também escala, além de o funcionário escolher. As
        # duas portas para o mesmo campo não se contradizem: a escolha do
        # funcionário é o caminho normal (D24), e esta é a correção de quem
        # coordena a noite, para remanejar alguém sem depender de ele estar com
        # o aparelho na mão.
        alvo = campos["showing_id"]
        if alvo is not None:
            permitidas = {s.showing_id for s in _sessoes_disponiveis(db, porteiro)}
            if alvo not in permitidas:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    "Sessão indisponível para este funcionário.")
        porteiro.gate_showing_id = alvo

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
    cada pessoa entrar, que é metade do motivo de a conta ser de gente e
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
    Sem esta lista, a resposta sai de cruzar duas colunas na cabeça, e o
    erro só aparece quando a fila já se formou (D26).

    A janela é a mesma da escolha de turno: o organizador enxerga exatamente
    as sessões que alguém pode assumir agora.

    Sem recorte por quem publicou: o painel administra um catálogo só, e a
    cobertura precisa concordar com ele (D29).
    """
    agora = datetime.now(timezone.utc)

    linhas = db.execute(
        select(Showing, Event, Room, Venue)
        .join(Event, Showing.event_id == Event.id)
        .join(Room, Showing.room_id == Room.id)
        .join(Venue, Room.venue_id == Venue.id)
        .where(
            # Sem recorte por quem publicou: a cobertura é da operação
            # inteira, como o resto do painel (D29).
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
    porteiros: dict[int, list[CoverageStaffOut]] = {}

    # Organizador entra junto: ele assume turno pelo próprio papel (D27), e
    # contar só `Role.GATE` fazia a sessão que ele estava atendendo aparecer
    # como "sem ninguém": a pergunta que esta lista existe para responder,
    # respondida errado (D33).
    for nome, sessao, papel in db.execute(
        select(User.name, User.gate_showing_id, User.role)
        .where(
            User.role.in_((Role.GATE, Role.ORGANIZER)),
            User.gate_showing_id.in_(ids),
        )
        .order_by(User.name)
    ):
        porteiros.setdefault(sessao, []).append(
            CoverageStaffOut(name=nome, organizer=papel == Role.ORGANIZER))

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
