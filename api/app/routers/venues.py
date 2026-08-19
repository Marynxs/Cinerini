"""Cinemas e salas. Cadastro do organizador, leitura pública."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.deps import DbSession, Organizer
from app.localidades import UFS, municipios, resolver
from app.models import Room, Seat, Showing, Ticket, TicketStatus, Venue
from app.schemas import (
    CityOut, MunicipioOut, RoomIn, RoomOut, RoomUpdate, UfOut, VenueIn,
    VenueOut, VenueUpdate,
)

router = APIRouter(prefix="/venues", tags=["cinemas e salas"])


def _venue_or_404(db: DbSession, venue_id: int) -> Venue:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cinema não encontrado.")
    return venue


@router.get("", response_model=list[VenueOut])
def list_venues(db: DbSession, city: int | None = None) -> list[Venue]:
    """`city` é o código do município no IBGE, não o nome (D23)."""
    stmt = select(Venue).order_by(Venue.city, Venue.name)
    if city:
        stmt = stmt.where(Venue.city_ibge_id == city)
    return list(db.scalars(stmt))


@router.get("/cities", response_model=list[CityOut])
def list_cities(db: DbSession) -> list[CityOut]:
    """Alimenta o filtro do catálogo, que começa pela cidade."""
    linhas = db.execute(
        select(Venue.city_ibge_id, Venue.city, Venue.state)
        .distinct()
        .order_by(Venue.city)
    ).all()

    return [CityOut(id=codigo, nome=nome, uf=uf) for codigo, nome, uf in linhas]


@router.get("/ufs", response_model=list[UfOut], tags=["localidades"])
def list_ufs() -> list[dict[str, str]]:
    """Constante, sem rede: são 27 e não mudam desde 1988 (D23)."""
    return UFS


@router.get("/ufs/{uf}/municipios", response_model=list[MunicipioOut],
            tags=["localidades"])
def list_municipios(uf: str) -> list[dict]:
    """Municípios da UF, para o cadastro escolher em vez de digitar."""
    return municipios(uf)


@router.post("", response_model=VenueOut, status_code=status.HTTP_201_CREATED)
def create_venue(data: VenueIn, db: DbSession, _: Organizer) -> Venue:
    """O nome da cidade vem do IBGE, com uma saída para quando ele não vem.

    Regra: o nome oficial sempre vence. O texto digitado só entra se o IBGE
    estiver fora, e existe porque a alternativa era o cadastro de cinema
    ficar refém de um serviço de terceiro (D28).
    """
    try:
        cidade = resolver(data.state, data.city_ibge_id)
    except HTTPException as erro:
        if erro.status_code != status.HTTP_503_SERVICE_UNAVAILABLE:
            raise
        if not data.city_fallback:
            raise
        cidade = data.city_fallback.strip()

    campos = data.model_dump(exclude={"city_fallback"})
    venue = Venue(**campos, city=cidade)
    db.add(venue)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Já existe um cinema com este nome nesta cidade.",
        )
    db.refresh(venue)
    return venue


@router.patch("/{venue_id}", response_model=VenueOut)
def update_venue(
    venue_id: int, data: VenueUpdate, db: DbSession, _: Organizer
) -> Venue:
    """Corrige o cadastro sem recriá-lo.

    Recriar não é opção: o cinema tem salas, e as salas têm sessões vendidas.
    Um erro de digitação no endereço obrigaria a desmontar tudo.
    """
    venue = _venue_or_404(db, venue_id)
    campos = data.model_dump(exclude_none=True)

    # UF e município andam juntos: mudar só um deixaria o código apontando
    # para outro estado, que é exatamente o que a D23 fecha.
    uf = campos.pop("state", None)
    codigo = campos.pop("city_ibge_id", None)

    if (uf is None) != (codigo is None):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Para mudar a cidade, informe a UF e o município juntos.",
        )

    if uf is not None:
        venue.city = resolver(uf, codigo)
        venue.state = uf
        venue.city_ibge_id = codigo

    for campo, valor in campos.items():
        setattr(venue, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Já existe um cinema com este nome nesta cidade.",
        )

    db.refresh(venue)
    return venue


@router.delete("/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_venue(venue_id: int, db: DbSession, _: Organizer) -> None:
    """Só sai se estiver vazio.

    Apagar em cascata levaria junto salas, sessões e ingressos vendidos — e
    quem comprou perderia o ingresso por causa de uma limpeza de cadastro.
    Exigir esvaziar antes torna a consequência visível passo a passo.
    """
    venue = _venue_or_404(db, venue_id)

    com_sala = db.scalar(select(Room.id).where(Room.venue_id == venue_id).limit(1))
    if com_sala is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este cinema ainda tem salas. Remova as salas antes.",
        )

    # A conta de funcionário perde o cinema por `ondelete=SET NULL`, e passa a
    # aparecer no painel como cadastro pela metade — que é o estado correto.
    db.delete(venue)
    db.commit()


@router.get("/{venue_id}/rooms", response_model=list[RoomOut])
def list_rooms(venue_id: int, db: DbSession) -> list[Room]:
    _venue_or_404(db, venue_id)
    return list(
        db.scalars(select(Room).where(Room.venue_id == venue_id).order_by(Room.name))
    )


@router.post(
    "/{venue_id}/rooms",
    response_model=RoomOut,
    status_code=status.HTTP_201_CREATED,
)
def create_room(venue_id: int, data: RoomIn, db: DbSession, _: Organizer) -> Room:
    _venue_or_404(db, venue_id)

    room = Room(venue_id=venue_id, **data.model_dump())
    db.add(room)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Já existe uma sala com este nome neste cinema.",
        )
    db.refresh(room)
    return room


def _recusa_encolher_sobre_venda(
    db: DbSession, room_id: int, campos: dict
) -> None:
    """Barra a redução que deixaria uma poltrona vendida fora da sala.

    Consulta o extremo já vendido em vez de percorrer ingresso por ingresso:
    basta a maior fileira e a maior poltrona, porque o mapa é retangular.
    Cancelado não conta, já que a poltrona voltou ao estoque.
    """
    novo_fileiras = campos.get("rows")
    novas_por_fileira = campos.get("seats_per_row")
    if novo_fileiras is None and novas_por_fileira is None:
        return

    extremos = db.execute(
        select(func.max(Seat.row_label), func.max(Seat.number))
        .join(Showing, Seat.showing_id == Showing.id)
        .join(Ticket, Ticket.seat_id == Seat.id)
        .where(
            Showing.room_id == room_id,
            Ticket.status != TicketStatus.CANCELLED,
        )
    ).one()

    fileira_vendida, numero_vendido = extremos
    if fileira_vendida is None:
        return

    # A fileira é uma letra só, gerada de `ascii_uppercase`, então a ordem
    # alfabética e a numérica coincidem.
    fileiras_necessarias = ord(fileira_vendida) - ord("A") + 1

    if novo_fileiras is not None and novo_fileiras < fileiras_necessarias:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Já há ingresso vendido na fileira {fileira_vendida} desta sala. "
            f"O layout não pode ficar com menos de {fileiras_necessarias} "
            "fileiras sem deixar esse ingresso sem lugar.",
        )

    if novas_por_fileira is not None and novas_por_fileira < numero_vendido:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Já há ingresso vendido na poltrona "
            f"{fileira_vendida}{numero_vendido} desta sala. O layout não pode "
            f"ficar com menos de {numero_vendido} poltronas por fileira sem "
            "deixar esse ingresso sem lugar.",
        )


@router.patch("/{venue_id}/rooms/{room_id}", response_model=RoomOut)
def update_room(
    venue_id: int, room_id: int, data: RoomUpdate, db: DbSession, _: Organizer
) -> Room:
    """Layout editável, menos onde encolher deixaria ingresso órfão.

    Os assentos pertencem à exibição e são gerados na publicação (D6), então
    mudar as dimensões vale para as próximas sessões e não reescreve mapa já
    vendido. Travar a edição por completo obrigaria a criar uma sala nova
    para corrigir um número errado no cadastro.

    O que é recusado é o subconjunto perigoso: encolher abaixo de uma
    poltrona já vendida. Sem esta checagem, a sala passava de 8x12 para 3x4
    com a H12 vendida, e o cliente ficava com ingresso de uma fileira que o
    cadastro diz não existir. É a mesma falha que a D9 impede ao trocar a
    sala de uma exibição, alcançada pela outra porta (D35).
    """
    room = db.get(Room, room_id)
    if room is None or room.venue_id != venue_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada.")

    campos = data.model_dump(exclude_none=True)
    _recusa_encolher_sobre_venda(db, room_id, campos)

    for campo, valor in campos.items():
        setattr(room, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Já existe uma sala com este nome neste cinema.",
        )

    db.refresh(room)
    return room


@router.delete("/{venue_id}/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(venue_id: int, room_id: int, db: DbSession, _: Organizer) -> None:
    room = db.get(Room, room_id)
    if room is None or room.venue_id != venue_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sala não encontrada.")

    # Verificado aqui e não deixado para o RESTRICT do banco porque o erro
    # precisa dizer o motivo. O banco recusaria de qualquer forma.
    em_uso = db.scalar(select(Showing.id).where(Showing.room_id == room_id).limit(1))
    if em_uso is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta sala tem sessões agendadas e não pode ser removida.",
        )

    db.delete(room)
    db.commit()
