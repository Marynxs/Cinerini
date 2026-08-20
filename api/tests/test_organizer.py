"""Cinemas, salas, eventos, sessões e a geração do mapa de assentos."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event as sa_event, func, select
from sqlalchemy.orm import Session

from app.models import (
    Event, Order, OrderStatus, Room, Seat, Showing, Ticket, TicketStatus,
    User,
    Venue,
)

AMANHA = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
CINEMA = {"name": "Cine Novo", "city_ibge_id": 4106902, "state": "PR",
          "address": "Rua XV, 100"}


def _vender(db: Session, showing: Showing, users: dict[str, User],
            label: str | None = None) -> Ticket:
    """Vende a primeira poltrona da sessão, ou a de rótulo pedido."""
    stmt = select(Seat).where(Seat.showing_id == showing.id)
    if label is not None:
        stmt = stmt.where(Seat.row_label == label[0],
                          Seat.number == int(label[1:]))
    assento = db.scalars(stmt.limit(1)).one()
    pedido = Order(customer_id=users["customer"].id, showing_id=showing.id,
                   total_cents=3200, status=OrderStatus.PAID)
    db.add(pedido)
    db.flush()

    ingresso = Ticket(order_id=pedido.id, seat_id=assento.id,
                      status=TicketStatus.VALID)
    db.add(ingresso)
    db.commit()
    return ingresso


@contextmanager
def _contando_idas(db: Session) -> Iterator[list[str]]:
    """Conta as instruções enviadas ao banco dentro do bloco."""
    idas: list[str] = []

    def anotar(conn, cursor, stmt, params, ctx, many) -> None:  # noqa: ANN001
        idas.append(stmt)

    bind = db.get_bind()
    sa_event.listen(bind, "before_cursor_execute", anotar)
    try:
        yield idas
    finally:
        sa_event.remove(bind, "before_cursor_execute", anotar)


class TestVenues:
    def test_organizer_creates_venue(self, client: TestClient, auth) -> None:
        r = client.post("/venues", json=CINEMA, headers=auth("organizer"))
        assert r.status_code == 201

    def test_state_is_normalised_to_uppercase(
        self, client: TestClient, auth
    ) -> None:
        """'pr' e 'PR' são a mesma UF; as duas formas quebrariam o filtro."""
        r = client.post("/venues", json={**CINEMA, "state": "pr"},
                        headers=auth("organizer"))
        assert r.json()["state"] == "PR"

    def test_same_name_in_same_city_is_rejected(
        self, client: TestClient, auth
    ) -> None:
        client.post("/venues", json=CINEMA, headers=auth("organizer"))
        r = client.post("/venues", json=CINEMA, headers=auth("organizer"))
        assert r.status_code == 409

    @pytest.mark.parametrize("papel", ["customer", "gate"])
    def test_only_organizer_creates(
        self, client: TestClient, auth, papel: str
    ) -> None:
        r = client.post("/venues", json=CINEMA, headers=auth(papel))
        assert r.status_code == 403

    def test_listing_is_public(self, client: TestClient, room: Room) -> None:
        assert client.get("/venues").status_code == 200

    def test_city_filter(self, client: TestClient, room: Room) -> None:
        """O filtro é pelo código do IBGE: nome de cidade se repete (D23)."""
        r = client.get("/venues", params={"city": 3550308})
        assert r.json()[0]["city"] == "São Paulo"

    def test_cities_feed_the_catalog_filter(
        self, client: TestClient, room: Room
    ) -> None:
        cidades = client.get("/venues/cities").json()
        assert {"id": 3550308, "nome": "São Paulo", "uf": "SP"} in cidades


class TestRooms:
    def test_capacity_is_derived(
        self, client: TestClient, auth, room: Room
    ) -> None:
        r = client.get(f"/venues/{room.venue_id}/rooms")
        assert r.json()[0]["capacity"] == 12

    def test_same_name_in_same_venue_is_rejected(
        self, client: TestClient, auth, room: Room
    ) -> None:
        r = client.post(f"/venues/{room.venue_id}/rooms",
                        json={"name": room.name, "rows": 5, "seats_per_row": 5},
                        headers=auth("organizer"))
        assert r.status_code == 409

    def test_more_rows_than_letters_is_rejected(
        self, client: TestClient, auth, room: Room
    ) -> None:
        """Cada fileira é uma letra de A a Z."""
        r = client.post(f"/venues/{room.venue_id}/rooms",
                        json={"name": "Sala 99", "rows": 27, "seats_per_row": 4},
                        headers=auth("organizer"))
        assert r.status_code == 422

    def test_room_with_showings_cannot_be_deleted(
        self, client: TestClient, auth, showing: Showing, room: Room
    ) -> None:
        r = client.delete(f"/venues/{room.venue_id}/rooms/{room.id}",
                          headers=auth("organizer"))
        assert r.status_code == 409


class TestEvents:
    def test_created_as_draft(self, client: TestClient, auth) -> None:
        r = client.post("/events", json={"title": "Filme Manual"},
                        headers=auth("organizer"))
        assert r.status_code == 201
        assert r.json()["status"] == "draft"

    def test_tmdb_fills_the_details(
        self, client: TestClient, auth, fake_tmdb
    ) -> None:
        """A ficha vem do catálogo: aceitá-la do corpo permitiria publicar
        um filme com dados que não são dele."""
        r = client.post("/events",
                        json={"tmdb_id": 603, "title": "Título Inventado"},
                        headers=auth("organizer"))
        assert r.json()["title"] == "Matrix"

    def test_without_tmdb_id_or_title_is_rejected(
        self, client: TestClient, auth
    ) -> None:
        assert client.post("/events", json={},
                           headers=auth("organizer")).status_code == 422

    def test_public_catalog_shows_only_published(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        client.post("/events", json={"title": "Rascunho"},
                    headers=auth("organizer"))
        titulos = [e["title"] for e in client.get("/events").json()]
        assert "Rascunho" not in titulos
        assert "Filme de Teste" in titulos


class TestPublishing:
    def _evento_com_sessao(self, client: TestClient, auth, room: Room) -> int:
        evento = client.post("/events", json={"title": "A Publicar"},
                             headers=auth("organizer")).json()
        client.post(f"/events/{evento['id']}/showings",
                    json={"room_id": room.id, "starts_at": AMANHA,
                          "price_cents": 3200},
                    headers=auth("organizer"))
        return evento["id"]

    def test_cannot_publish_without_showings(
        self, client: TestClient, auth
    ) -> None:
        evento = client.post("/events", json={"title": "Vazio"},
                             headers=auth("organizer")).json()
        r = client.post(f"/events/{evento['id']}/publish",
                        headers=auth("organizer"))
        assert r.status_code == 409

    def test_a_new_showing_already_has_its_seat_map(
        self, client: TestClient, auth, room: Room
    ) -> None:
        """Mapa na criação, e não só na publicação.

        Adiar fazia a sessão recém-criada de um rascunho anunciar ocupação
        0/0 no painel, número que é indistinguível de uma sala vazia de
        verdade.
        """
        evento_id = self._evento_com_sessao(client, auth, room)
        sessao = client.get(f"/events/{evento_id}/showings").json()[0]

        assert sessao["seats_total"] == 12
        assert len(client.get(f"/showings/{sessao['id']}/seats").json()) == 12

    def test_rows_are_lettered_from_a(
        self, client: TestClient, showing: Showing
    ) -> None:
        assentos = client.get(f"/showings/{showing.id}/seats").json()
        assert {a["row_label"] for a in assentos} == {"A", "B", "C"}

    def test_first_row_has_two_accessible_seats(
        self, client: TestClient, showing: Showing
    ) -> None:
        """Fileira A: piso plano, sem os degraus da arquibancada."""
        assentos = client.get(f"/showings/{showing.id}/seats").json()
        acessiveis = [a for a in assentos if a["kind"] == "accessible"]
        assert len(acessiveis) == 2
        assert all(a["row_label"] == "A" for a in acessiveis)

    def test_publishing_does_not_duplicate_seats(
        self, client: TestClient, auth, room: Room
    ) -> None:
        """A publicação ainda gera o mapa das sessões antigas, sem repetir."""
        evento_id = self._evento_com_sessao(client, auth, room)
        sessao = client.get(f"/events/{evento_id}/showings").json()[0]

        client.post(f"/events/{evento_id}/publish", headers=auth("organizer"))
        client.post(f"/events/{evento_id}/publish", headers=auth("organizer"))

        assert len(client.get(f"/showings/{sessao['id']}/seats").json()) == 12

    def test_unpublishing_keeps_seats_and_tickets(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        """Quem comprou continua com ingresso válido; muda a visibilidade."""
        client.post(f"/events/{showing.event_id}/unpublish",
                    headers=auth("organizer"))
        assert len(client.get(f"/showings/{showing.id}/seats").json()) == 12


class TestSharedCatalog:
    """O catálogo é de uma operação só, não de cada organizador (D29)."""

    def test_any_organizer_publishes(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        r = client.post(f"/events/{showing.event_id}/publish",
                        headers=auth("organizer2"))
        assert r.status_code == 200

    def test_any_organizer_edits_a_showing(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        r = client.patch(f"/showings/{showing.id}", json={"price_cents": 1000},
                         headers=auth("organizer2"))
        assert r.status_code == 200

    def test_the_managed_list_is_the_same_for_everyone(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        """Duas listas diferentes fariam a equipe discordar do que existe."""
        um = client.get("/events/managed", headers=auth("organizer")).json()
        outro = client.get("/events/managed", headers=auth("organizer2")).json()

        assert [e["id"] for e in um] == [e["id"] for e in outro]

    def test_a_missing_event_is_still_404(
        self, client: TestClient, auth
    ) -> None:
        """Some a cerca de dono, não a checagem de existência."""
        r = client.post("/events/999999999/publish", headers=auth("organizer"))
        assert r.status_code == 404

    def test_customer_still_cannot_publish(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        """Unificar é entre organizadores, não com o resto do mundo."""
        r = client.post(f"/events/{showing.event_id}/publish",
                        headers=auth("customer"))
        assert r.status_code == 403


class TestRoomChange:
    """Decisão D9: a sala trava na primeira venda, não na publicação."""

    @pytest.fixture
    def sala_menor(self, client: TestClient, auth, room: Room) -> dict:
        return client.post(f"/venues/{room.venue_id}/rooms",
                           json={"name": "Sala Menor", "rows": 2,
                                 "seats_per_row": 2},
                           headers=auth("organizer")).json()

    def test_without_sales_the_map_is_rebuilt(
        self, client: TestClient, auth, showing: Showing, sala_menor: dict
    ) -> None:
        r = client.patch(f"/showings/{showing.id}",
                         json={"room_id": sala_menor["id"]},
                         headers=auth("organizer"))
        assert r.status_code == 200
        assert len(client.get(f"/showings/{showing.id}/seats").json()) == 4

    def test_with_sales_the_change_is_refused(
        self, client: TestClient, auth, db: Session, showing: Showing,
        users: dict[str, User], sala_menor: dict,
    ) -> None:
        _vender(db, showing, users)

        r = client.patch(f"/showings/{showing.id}",
                         json={"room_id": sala_menor["id"]},
                         headers=auth("organizer"))
        assert r.status_code == 409
        assert len(client.get(f"/showings/{showing.id}/seats").json()) == 12

    def test_price_stays_editable_after_sales(
        self, client: TestClient, auth, db: Session, showing: Showing,
        users: dict[str, User],
    ) -> None:
        """Promoção é operação corriqueira; quem comprou pagou o registrado."""
        _vender(db, showing, users)

        r = client.patch(f"/showings/{showing.id}", json={"price_cents": 2800},
                         headers=auth("organizer"))
        assert r.status_code == 200

    def test_showing_with_tickets_cannot_be_deleted(
        self, client: TestClient, auth, db: Session, showing: Showing,
        users: dict[str, User],
    ) -> None:
        _vender(db, showing, users)

        r = client.delete(f"/showings/{showing.id}", headers=auth("organizer"))
        assert r.status_code == 409


class TestDeletingShowings:
    """Sair do sistema é o fim de um caminho, não um botão (D36)."""

    def test_showing_without_tickets_is_deleted(
        self, client: TestClient, auth, showing: Showing,
    ) -> None:
        r = client.delete(f"/showings/{showing.id}", headers=auth("organizer"))
        assert r.status_code == 204
        assert client.get(f"/showings/{showing.id}").status_code == 404

    def test_cancelling_opens_the_way_to_delete(
        self, client: TestClient, auth, db: Session, showing: Showing,
        users: dict[str, User],
    ) -> None:
        """O cancelamento é o passo que avisa quem comprou, e só ele libera."""
        _vender(db, showing, users)

        assert client.delete(f"/showings/{showing.id}",
                             headers=auth("organizer")).status_code == 409

        assert client.post(f"/showings/{showing.id}/cancel",
                           json={"reason": "Projetor quebrado"},
                           headers=auth("organizer")).status_code == 200

        r = client.delete(f"/showings/{showing.id}", headers=auth("organizer"))
        assert r.status_code == 204

    def test_deleting_takes_seats_orders_and_tickets_along(
        self, client: TestClient, auth, db: Session, showing: Showing,
        users: dict[str, User],
    ) -> None:
        """Nenhuma dessas chaves tem cascata: sobrariam linhas órfãs."""
        ingresso = _vender(db, showing, users)
        pedido_id = ingresso.order_id

        client.post(f"/showings/{showing.id}/cancel",
                    json={"reason": "Sala interditada"},
                    headers=auth("organizer"))
        assert client.delete(f"/showings/{showing.id}",
                             headers=auth("organizer")).status_code == 204

        assert db.get(Order, pedido_id) is None
        assert db.scalar(select(func.count(Ticket.id))
                         .where(Ticket.order_id == pedido_id)) == 0
        assert db.scalar(select(func.count(Seat.id))
                         .where(Seat.showing_id == showing.id)) == 0

    def test_a_used_ticket_blocks_deletion_for_good(
        self, client: TestClient, auth, db: Session, showing: Showing,
        users: dict[str, User],
    ) -> None:
        """Alguém entrou. Apagar a linha falsificaria a garantia 3."""
        ingresso = _vender(db, showing, users)
        ingresso.status = TicketStatus.USED
        db.commit()

        client.post(f"/showings/{showing.id}/cancel",
                    json={"reason": "Tarde demais"},
                    headers=auth("organizer"))

        r = client.delete(f"/showings/{showing.id}", headers=auth("organizer"))
        assert r.status_code == 409
        assert "portaria" in r.json()["detail"]


class TestQueryBudget:
    """N+1 é invisível aqui e domina em produção.

    O custo do padrão é o número de idas ao banco, não o trabalho de cada
    uma. Na mesma máquina a ida é quase de graça e nada aparece; com a API
    no Render e o banco no Neon, listar as sessões de um evento levava nove
    segundos. Contar as idas é a única forma de o defeito falhar num teste.
    """

    def _sessoes(self, client: TestClient, auth, room: Room,
                 quantas: int) -> int:
        evento = client.post("/events", json={"title": "Com Muitas Sessões"},
                             headers=auth("organizer")).json()
        for dia in range(1, quantas + 1):
            quando = (datetime.now(timezone.utc) + timedelta(days=dia)).isoformat()
            client.post(f"/events/{evento['id']}/showings",
                        json={"room_id": room.id, "starts_at": quando,
                              "price_cents": 3200, "audio": "Dublado"},
                        headers=auth("organizer"))
        return evento["id"]

    def test_listing_showings_costs_the_same_for_one_and_for_many(
        self, client: TestClient, auth, db: Session, room: Room
    ) -> None:
        poucas = self._sessoes(client, auth, room, 1)
        muitas = self._sessoes(client, auth, room, 12)

        with _contando_idas(db) as uma:
            assert len(client.get(f"/events/{poucas}/showings").json()) == 1

        with _contando_idas(db) as doze:
            assert len(client.get(f"/events/{muitas}/showings").json()) == 12

        assert len(doze) == len(uma), (
            f"a rota passou de {len(uma)} para {len(doze)} idas ao banco ao "
            "sair de 1 para 12 sessões: o custo voltou a crescer com o "
            "número de linhas"
        )

    def test_the_public_catalogue_does_not_grow_with_the_showings(
        self, client: TestClient, auth, db: Session, room: Room
    ) -> None:
        evento = self._sessoes(client, auth, room, 12)
        client.post(f"/events/{evento}/publish", headers=auth("organizer"))

        with _contando_idas(db) as idas:
            assert client.get("/events").status_code == 200

        assert len(idas) <= 5, (
            f"o catálogo público fez {len(idas)} idas ao banco; ele resolve "
            "todas as sessões em lote e não deveria passar disso"
        )


class TestEditingVenues:
    """Cadastro errado se corrige; recriar levaria salas e vendas junto."""

    def test_renames_a_venue(self, client: TestClient, auth, room: Room) -> None:
        r = client.patch(f"/venues/{room.venue_id}", json={"name": "Cine Rebatizado"},
                         headers=auth("organizer"))
        assert r.status_code == 200
        assert r.json()["name"] == "Cine Rebatizado"

    def test_changes_the_city_with_uf_and_code_together(
        self, client: TestClient, auth, room: Room
    ) -> None:
        r = client.patch(f"/venues/{room.venue_id}",
                         json={"state": "PR", "city_ibge_id": 4106902},
                         headers=auth("organizer"))
        assert r.status_code == 200
        assert r.json()["city"] == "Curitiba"
        assert r.json()["city_ibge_id"] == 4106902

    def test_city_without_uf_is_refused(
        self, client: TestClient, auth, room: Room
    ) -> None:
        """Mudar só um deixaria o código apontando para outro estado (D23)."""
        r = client.patch(f"/venues/{room.venue_id}", json={"city_ibge_id": 4106902},
                         headers=auth("organizer"))
        assert r.status_code == 422

    def test_only_organizer_edits(
        self, client: TestClient, auth, room: Room
    ) -> None:
        r = client.patch(f"/venues/{room.venue_id}", json={"name": "X"},
                         headers=auth("customer"))
        assert r.status_code == 403


class TestRemovingVenues:
    def test_venue_with_rooms_is_refused(
        self, client: TestClient, auth, room: Room
    ) -> None:
        """Cascata levaria salas, sessões e ingressos vendidos junto."""
        r = client.delete(f"/venues/{room.venue_id}", headers=auth("organizer"))
        assert r.status_code == 409

    def test_empty_venue_is_removed(
        self, client: TestClient, auth, db: Session
    ) -> None:
        criado = client.post("/venues", json=CINEMA,
                             headers=auth("organizer")).json()

        r = client.delete(f"/venues/{criado['id']}", headers=auth("organizer"))
        assert r.status_code == 204
        assert db.get(Venue, criado["id"]) is None

    def test_removing_a_venue_unlinks_its_staff(
        self, client: TestClient, auth, db: Session
    ) -> None:
        """`ondelete=SET NULL`: a conta vira cadastro pela metade, não some."""
        criado = client.post("/venues", json=CINEMA,
                             headers=auth("organizer")).json()
        gate = client.post(f"/venues/{criado['id']}/gates", json={
            "name": "Porta", "email": "porta.orfa@cinerini.com.br",
            "password": "senhaDaPortaria1"}, headers=auth("organizer")).json()

        client.delete(f"/venues/{criado['id']}", headers=auth("organizer"))

        depois = client.get("/gates", headers=auth("organizer")).json()
        alvo = next(g for g in depois if g["id"] == gate["id"])
        assert alvo["venue_id"] is None


class TestEditingRooms:
    def test_renames_a_room(
        self, client: TestClient, auth, room: Room
    ) -> None:
        r = client.patch(f"/venues/{room.venue_id}/rooms/{room.id}",
                         json={"name": "Sala VIP"}, headers=auth("organizer"))
        assert r.status_code == 200
        assert r.json()["name"] == "Sala VIP"

    def test_layout_change_updates_capacity(
        self, client: TestClient, auth, room: Room
    ) -> None:
        r = client.patch(f"/venues/{room.venue_id}/rooms/{room.id}",
                         json={"rows": 5, "seats_per_row": 10},
                         headers=auth("organizer"))
        assert r.json()["capacity"] == 50

    def test_layout_change_does_not_touch_sold_maps(
        self, client: TestClient, auth, db: Session, showing: Showing,
        room: Room
    ) -> None:
        """Assentos pertencem à exibição e já foram gerados (D6)."""
        antes = db.scalar(
            select(func.count(Seat.id)).where(Seat.showing_id == showing.id))

        client.patch(f"/venues/{room.venue_id}/rooms/{room.id}",
                     json={"rows": 2, "seats_per_row": 2},
                     headers=auth("organizer"))

        depois = db.scalar(
            select(func.count(Seat.id)).where(Seat.showing_id == showing.id))
        assert depois == antes

    def test_shrinking_below_a_sold_row_is_refused(
        self, client: TestClient, auth, db: Session, showing: Showing,
        room: Room, users: dict[str, User]
    ) -> None:
        """A D9 impede trocar a sala da exibição depois da venda. Encolher a
        própria sala chegava ao mesmo estrago pela outra porta: a poltrona
        vendida ficava numa fileira que o cadastro passa a negar (D35)."""
        _vender(db, showing, users, label="C4")

        r = client.patch(f"/venues/{room.venue_id}/rooms/{room.id}",
                         json={"rows": 2}, headers=auth("organizer"))

        assert r.status_code == 409
        assert "fileira C" in r.json()["detail"]

    def test_shrinking_below_a_sold_seat_number_is_refused(
        self, client: TestClient, auth, db: Session, showing: Showing,
        room: Room, users: dict[str, User]
    ) -> None:
        _vender(db, showing, users, label="C4")

        r = client.patch(f"/venues/{room.venue_id}/rooms/{room.id}",
                         json={"seats_per_row": 2}, headers=auth("organizer"))

        assert r.status_code == 409
        assert "C4" in r.json()["detail"]

    def test_growing_is_allowed_with_tickets_sold(
        self, client: TestClient, auth, db: Session, showing: Showing,
        room: Room, users: dict[str, User]
    ) -> None:
        """Só o encolhimento perigoso é barrado. Corrigir um número para
        cima nunca deixa ingresso sem lugar."""
        _vender(db, showing, users, label="C4")

        r = client.patch(f"/venues/{room.venue_id}/rooms/{room.id}",
                         json={"rows": 10, "seats_per_row": 20},
                         headers=auth("organizer"))

        assert r.status_code == 200
        assert r.json()["capacity"] == 200

    def test_renaming_is_allowed_with_tickets_sold(
        self, client: TestClient, auth, db: Session, showing: Showing,
        room: Room, users: dict[str, User]
    ) -> None:
        _vender(db, showing, users, label="C4")

        r = client.patch(f"/venues/{room.venue_id}/rooms/{room.id}",
                         json={"name": "Sala Renomeada"},
                         headers=auth("organizer"))

        assert r.status_code == 200

    def test_cancelled_ticket_does_not_block_shrinking(
        self, client: TestClient, auth, db: Session, showing: Showing,
        room: Room, users: dict[str, User]
    ) -> None:
        """Cancelado devolveu a poltrona ao estoque, então não há lugar a
        preservar. É a mesma cláusula do índice único parcial."""
        ingresso = _vender(db, showing, users, label="C4")
        ingresso.status = TicketStatus.CANCELLED
        db.commit()

        r = client.patch(f"/venues/{room.venue_id}/rooms/{room.id}",
                         json={"rows": 2, "seats_per_row": 2},
                         headers=auth("organizer"))

        assert r.status_code == 200

    def test_room_of_another_venue_is_404(
        self, client: TestClient, auth, room: Room
    ) -> None:
        r = client.patch(f"/venues/999999999/rooms/{room.id}",
                         json={"name": "X"}, headers=auth("organizer"))
        assert r.status_code == 404


class TestCityFallback:
    """O cadastro de cinema não fica refém do IBGE (D28)."""

    @pytest.fixture
    def ibge_fora(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi import HTTPException, status

        from app import localidades

        def _cai(uf: str):
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "IBGE indisponível.")

        monkeypatch.setattr(localidades, "municipios", _cai)
        localidades.clear_cache()

    def test_without_the_ibge_and_without_fallback_it_refuses(
        self, client: TestClient, auth, ibge_fora: None
    ) -> None:
        """Sem nome nenhum não dá para gravar: a coluna não aceita vazio."""
        r = client.post("/venues", json=CINEMA, headers=auth("organizer"))
        assert r.status_code == 503

    def test_the_typed_name_is_used_when_the_ibge_is_down(
        self, client: TestClient, auth, ibge_fora: None
    ) -> None:
        r = client.post("/venues",
                        json={**CINEMA, "city_fallback": "Curitiba"},
                        headers=auth("organizer"))

        assert r.status_code == 201
        assert r.json()["city"] == "Curitiba"

    @pytest.fixture
    def ibge_no_ar(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Dublê do IBGE respondendo, em vez da API de verdade.

        Este era o único caso da suíte padrão que saía para a rede: o teste
        anterior limpa o cache, então a consulta acontecia toda vez e falhava
        quando o IBGE demorava. A regra do projeto é que a suíte padrão roda
        sem rede, e teste de contrato fica atrás de `-m contract`.
        """
        from app import localidades

        monkeypatch.setattr(
            localidades, "municipios",
            lambda uf: [{"id": 4106902, "nome": "Curitiba"}])
        localidades.clear_cache()

    def test_the_official_name_wins_when_the_ibge_answers(
        self, client: TestClient, auth, ibge_no_ar: None
    ) -> None:
        """Com o IBGE no ar o texto digitado é ignorado, e é o ponto todo."""
        r = client.post("/venues",
                        json={**CINEMA, "city_fallback": "cutiriba errado"},
                        headers=auth("organizer"))

        assert r.status_code == 201
        assert r.json()["city"] == "Curitiba"


class TestDraftLifecycle:
    """Rascunho é o único estado em que apagar não destrói prova de compra."""

    # Fora da lista do seed: a regra de unicidade é global, e reusar um
    # filme semeado faria o teste medir o cenário em vez do comportamento.
    FILME = 157336

    def _rascunho(self, client: TestClient, auth) -> dict:
        return client.post("/events", json={"tmdb_id": self.FILME},
                           headers=auth("organizer")).json()

    def test_the_same_film_is_refused_twice(
        self, client: TestClient, auth, fake_tmdb
    ) -> None:
        """Dois eventos do mesmo filme repartiriam as sessões (D30)."""
        self._rascunho(client, auth)
        r = client.post("/events", json={"tmdb_id": self.FILME},
                        headers=auth("organizer"))

        assert r.status_code == 409

    def test_the_refusal_names_the_existing_event(
        self, client: TestClient, auth, fake_tmdb
    ) -> None:
        """Sem o nome, quem recebe o erro não sabe onde criar a sessão."""
        self._rascunho(client, auth)
        r = client.post("/events", json={"tmdb_id": self.FILME},
                        headers=auth("organizer"))

        assert "Interestelar" in r.json()["detail"]

    def test_an_empty_draft_is_removed(
        self, client: TestClient, auth, db: Session, fake_tmdb
    ) -> None:
        rascunho = self._rascunho(client, auth)

        r = client.delete(f"/events/{rascunho['id']}", headers=auth("organizer"))
        assert r.status_code == 204
        assert db.get(Event, rascunho["id"]) is None

    def test_a_draft_with_showings_is_refused(
        self, client: TestClient, auth, room: Room, fake_tmdb
    ) -> None:
        rascunho = self._rascunho(client, auth)
        client.post(f"/events/{rascunho['id']}/showings",
                    json={"room_id": room.id, "starts_at": AMANHA,
                          "price_cents": 3000, "audio": "Dublado"},
                    headers=auth("organizer"))

        r = client.delete(f"/events/{rascunho['id']}", headers=auth("organizer"))
        assert r.status_code == 409

    def test_a_published_event_is_refused(
        self, client: TestClient, auth, showing: Showing
    ) -> None:
        """Publicado pode ter ingresso vendido: apagar levaria o comprovante."""
        r = client.delete(f"/events/{showing.event_id}",
                          headers=auth("organizer"))
        assert r.status_code == 409

    def test_unpublishing_reopens_the_door(
        self, client: TestClient, auth, db: Session, fake_tmdb
    ) -> None:
        """Despublicar volta ao rascunho, e aí a remoção passa a valer."""
        rascunho = self._rascunho(client, auth)
        client.post(f"/events/{rascunho['id']}/publish", headers=auth("organizer"))
        client.post(f"/events/{rascunho['id']}/unpublish", headers=auth("organizer"))

        r = client.delete(f"/events/{rascunho['id']}", headers=auth("organizer"))
        assert r.status_code == 204

    def test_only_organizer_removes(
        self, client: TestClient, auth, fake_tmdb
    ) -> None:
        rascunho = self._rascunho(client, auth)
        r = client.delete(f"/events/{rascunho['id']}", headers=auth("customer"))
        assert r.status_code == 403
