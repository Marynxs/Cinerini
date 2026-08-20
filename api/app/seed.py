"""Popula o banco com o cenário mínimo para percorrer o fluxo inteiro.

    python -m app.seed            semeia se estiver vazio
    python -m app.seed --reset    apaga tudo e semeia de novo

Idempotente: rodar duas vezes não duplica nada. Sem isso, o avaliador que
executasse o comando por engano acabaria com dois catálogos sobrepostos.
"""

import argparse
import sys
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Event,
    EventStatus,
    Role,
    Room,
    Seat,
    Showing,
    User,
    Venue,
)
from app.seating import generate_seats
from app.security import hash_password
from app.tmdb import movie_details

SENHA = "cinerini123"

# Domínio comum e não um TLD reservado como .test ou .local: o validador de
# e-mail recusa reservados, e as contas semeadas ficariam impossíveis de usar
# pela API mesmo existindo no banco.
USUARIOS = [
    ("Marina Alencar", "organizador@cinerini.com.br", Role.ORGANIZER),
    ("Bruno Tavares", "cliente1@cinerini.com.br", Role.CUSTOMER),
    ("Carla Nogueira", "cliente2@cinerini.com.br", Role.CUSTOMER),
    ("Portaria Sala 1", "portaria@cinerini.com.br", Role.GATE),
]

# O código do IBGE vem escrito e não resolvido pela rede: o seed precisa
# rodar sem internet, e é ele que garante um cenário reproduzível (D23).
VENUES = [
    ("Cine Belas Artes", 3550308, "São Paulo", "SP", "Rua da Consolação, 2423"),
    ("Cine Odeon", 3304557, "Rio de Janeiro", "RJ", "Praça Floriano, 7"),
]

# (cinema, nome, fileiras, poltronas por fileira)
SALAS = [
    (0, "Sala 1", 8, 12),
    (0, "Sala 2", 5, 8),
    (1, "Sala Única", 6, 10),
]

# Filmes reais do TMDb. Se a chave não estiver configurada, o seed cai para
# a ficha embutida, porque o avaliador precisa conseguir semear mesmo sem ter
# pedido chave própria ao TMDb.
FILMES = [
    (693134, "Duna: Parte Dois"),
    (299534, "Vingadores: Ultimato"),
    (27205, "A Origem"),
]

FICHA_RESERVA = {
    693134: {
        "title": "Duna: Parte Dois",
        "synopsis": "Paul Atreides se une a Chani e aos Fremen enquanto "
                    "busca vingança contra os conspiradores que destruíram "
                    "sua família.",
        "runtime_minutes": 167,
    },
    299534: {
        "title": "Vingadores: Ultimato",
        "synopsis": "Após os eventos devastadores de Guerra Infinita, os "
                    "Vingadores restantes se unem para reverter as ações de "
                    "Thanos.",
        "runtime_minutes": 181,
    },
    27205: {
        "title": "A Origem",
        "synopsis": "Um ladrão que invade sonhos para roubar segredos recebe "
                    "a missão inversa: plantar uma ideia na mente de um "
                    "herdeiro.",
        "runtime_minutes": 148,
    },
}


def _ficha(tmdb_id: int) -> dict:
    try:
        return movie_details(tmdb_id)
    except Exception:
        # Falta de chave, rede fora ou TMDb indisponível não podem impedir o
        # seed: sem cenário, nada do fluxo é demonstrável.
        print(f"  ! TMDb indisponível para {tmdb_id}, usando ficha embutida")
        return {"tmdb_id": tmdb_id, "poster_url": None,
                "backdrop_url": None, **FICHA_RESERVA[tmdb_id]}


# Horário de Brasília. Declarado explicitamente para que as sessões caiam nos
# horários que um cinema realmente usa, já que combinar em UTC jogaria a sessão da
# noite para o dia seguinte no banco.
BRT = timezone(timedelta(hours=-3))

HORARIOS_DO_DIA = (time(14, 0), time(18, 30), time(21, 40))

# Uma sessão a cada dois dias, por três semanas. O seed é um retrato tirado
# uma vez, e o banco é visitado dias depois: a agenda de dois dias que havia
# aqui deixava o catálogo vazio na quarta-feira seguinte, porque o catálogo
# só lista sessão futura. O passo de dois dias é o maior que ainda mantém
# sempre uma sessão dentro da janela da portaria, que enxerga JANELA_ADIANTE
# à frente, sem encher a tabela do painel.
DIAS_DA_AGENDA = tuple(range(1, 22, 2))


def _agenda(indice_do_filme: int) -> list[datetime]:
    """Os horários de um filme ao longo da agenda.

    O horário roda por dia e por filme. Sem o deslocamento os três filmes
    estreariam todos às 14h do mesmo dia, e o catálogo pareceria ter uma
    sessão só, repetida.
    """
    hoje = datetime.now(BRT).date()
    return [
        datetime.combine(
            hoje + timedelta(days=dia),
            HORARIOS_DO_DIA[(indice_do_filme + k) % len(HORARIOS_DO_DIA)],
            tzinfo=BRT,
        )
        for k, dia in enumerate(DIAS_DA_AGENDA)
    ]


# Ordem inversa das dependências: filho antes do pai. `share_links` abre a
# lista porque referencia tickets, e users fecha porque gate_showing_id
# referencia showings e gate_venue_id referencia venues.
TABELAS = ("share_links", "tickets", "orders", "seats", "showings",
           "events", "rooms", "venues", "users")


def limpar(db: Session) -> None:
    for tabela in TABELAS:
        db.execute(text(f"DELETE FROM {tabela}"))
    db.commit()


def semear(db: Session) -> None:
    print("Semeando...")

    usuarios = {}
    for nome, email, papel in USUARIOS:
        u = User(name=nome, email=email,
                 password_hash=hash_password(SENHA), role=papel)
        db.add(u)
        usuarios[papel] = usuarios.get(papel, []) + [u]
    db.flush()
    print(f"  {len(USUARIOS)} usuários")

    organizador = usuarios[Role.ORGANIZER][0]

    venues = []
    for nome, ibge, cidade, uf, endereco in VENUES:
        v = Venue(name=nome, city=cidade, city_ibge_id=ibge,
                  state=uf, address=endereco)
        db.add(v)
        venues.append(v)
    db.flush()
    print(f"  {len(venues)} cinemas")

    salas = []
    for idx, nome, fileiras, por_fileira in SALAS:
        r = Room(venue_id=venues[idx].id, name=nome,
                 rows=fileiras, seats_per_row=por_fileira)
        db.add(r)
        salas.append(r)
    db.flush()
    print(f"  {len(salas)} salas")

    cidade_da_sala = {
        sala.id: venue.city
        for sala in salas
        for venue in venues
        if venue.id == sala.venue_id
    }

    total_sessoes = 0

    for i, (tmdb_id, rotulo) in enumerate(FILMES):
        print(f"  buscando {rotulo}...")
        evento = Event(organizer_id=organizador.id,
                       status=EventStatus.PUBLISHED, **_ficha(tmdb_id))
        db.add(evento)
        db.flush()

        # Cada filme ocupa uma sala e percorre a agenda inteira: é o que
        # mantém os três em cartaz ao mesmo tempo, em datas diferentes.
        sala = salas[i % len(salas)]
        horarios = _agenda(i)
        agenda = [(sala, h) for h in horarios]

        # O primeiro filme ganha sessões num cinema de outra cidade. Sem isso
        # não há como demonstrar o agrupamento por cinema nem o filtro por
        # cidade: com um filme por local, os dois parecem não fazer nada.
        if i == 0:
            fora = next(s for s in salas
                        if cidade_da_sala[s.id] != cidade_da_sala[sala.id])
            agenda += [(fora, h) for h in horarios[1:3]]

        primeira = None

        for sala_da_vez, h in agenda:
            s = Showing(
                event_id=evento.id,
                room_id=sala_da_vez.id,
                starts_at=h,
                price_cents=3200 if sala_da_vez.rows > 5 else 2600,
                audio="Dublado" if total_sessoes % 2 == 0 else "Legendado",
            )
            db.add(s)
            db.flush()
            generate_seats(db, s)
            total_sessoes += 1
            primeira = primeira or s

        # A portaria trabalha no cinema da primeira sessão do primeiro filme,
        # e nasce **sem turno escolhido**: escolher é o primeiro gesto de quem
        # opera, e deixá-lo pronto esconderia o passo (D24). Esse cinema dá os
        # dois recusados de uma vez: as outras sessões do mesmo filme
        # demonstram "outra sessão", e os demais filmes, "outro evento".
        if i == 0 and primeira is not None:
            sala_da_primeira = next(s for s in salas if s.id == primeira.room_id)
            usuarios[Role.GATE][0].gate_venue_id = sala_da_primeira.venue_id

    db.commit()

    assentos = db.scalar(select(func.count(Seat.id)))
    print(f"  {len(FILMES)} eventos publicados")
    print(f"  {total_sessoes} sessões")
    print(f"  {assentos} assentos gerados")


def main() -> int:
    parser = argparse.ArgumentParser(description="Popula o banco.")
    parser.add_argument("--reset", action="store_true",
                        help="Apaga os dados existentes antes de semear.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existentes = db.scalar(select(func.count(User.id))) or 0

        if existentes and not args.reset:
            print(f"Banco já tem {existentes} usuários. Nada a fazer.")
            print("Use --reset para apagar e semear de novo.")
            return 0

        if args.reset:
            print("Apagando dados existentes...")
            limpar(db)

        semear(db)

        print()
        print("Contas criadas. Senha de todas: " + SENHA)
        for nome, email, papel in USUARIOS:
            print(f"  {papel.value:<10} {email:<32} {nome}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
