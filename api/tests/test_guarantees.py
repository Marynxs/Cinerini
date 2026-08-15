"""As quatro garantias inegociáveis, verificadas contra o banco real.

Não são testes de rota: exercitam as constraints e as operações atômicas
diretamente, porque é onde a correção mora. Uma rota pode ser reescrita; a
regra não pode ser enfraquecida.
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Order, OrderStatus, Seat, Showing, Ticket, TicketStatus, User


@pytest.fixture
def seat(db: Session, showing: Showing) -> Seat:
    return db.scalars(select(Seat).where(Seat.showing_id == showing.id)).first()


@pytest.fixture
def order(db: Session, showing: Showing, users: dict[str, User]) -> Order:
    o = Order(customer_id=users["customer"].id, showing_id=showing.id,
              total_cents=3200, status=OrderStatus.PAID)
    db.add(o)
    db.commit()
    return o


@pytest.fixture
def order2(db: Session, showing: Showing, users: dict[str, User]) -> Order:
    o = Order(customer_id=users["customer2"].id, showing_id=showing.id,
              total_cents=3200, status=OrderStatus.PAID)
    db.add(o)
    db.commit()
    return o


class TestSeatSoldOnlyOnce:
    """Garantia 1: o mesmo assento nunca tem dois ingressos vivos."""

    def test_second_ticket_on_same_seat_is_rejected(
        self, db: Session, seat: Seat, order: Order, order2: Order
    ) -> None:
        db.add(Ticket(order_id=order.id, seat_id=seat.id,
                      status=TicketStatus.VALID))
        db.commit()

        db.add(Ticket(order_id=order2.id, seat_id=seat.id,
                      status=TicketStatus.VALID))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_held_ticket_also_blocks_the_seat(
        self, db: Session, seat: Seat, order: Order, order2: Order
    ) -> None:
        """Assento em checkout está travado, mesmo sem pagamento concluído."""
        db.add(Ticket(order_id=order.id, seat_id=seat.id,
                      status=TicketStatus.HELD))
        db.commit()

        db.add(Ticket(order_id=order2.id, seat_id=seat.id,
                      status=TicketStatus.VALID))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_cancelling_returns_the_seat_to_stock(
        self, db: Session, seat: Seat, order: Order, order2: Order
    ) -> None:
        """O índice é parcial justamente para permitir isto."""
        primeiro = Ticket(order_id=order.id, seat_id=seat.id,
                          status=TicketStatus.VALID)
        db.add(primeiro)
        db.commit()

        primeiro.status = TicketStatus.CANCELLED
        db.commit()

        db.add(Ticket(order_id=order2.id, seat_id=seat.id,
                      status=TicketStatus.VALID))
        db.commit()  # não deve levantar

    def test_index_is_partial_in_the_database(self, db: Session) -> None:
        """A garantia precisa estar no schema, não só no comportamento."""
        definicao = db.scalar(text(
            "select indexdef from pg_indexes where indexname='uq_seat_ocupado'"
        ))
        assert definicao is not None, "índice da garantia não existe"
        assert "UNIQUE" in definicao
        assert "WHERE" in definicao and "cancelled" in definicao


class TestTicketValidatedOnlyOnce:
    """Garantia 3: validação é um update condicional atômico."""

    UPDATE = text(
        "UPDATE tickets SET status='used', used_at=now() "
        "WHERE id=:id AND status='valid'"
    )

    def test_first_validation_affects_one_row(
        self, db: Session, seat: Seat, order: Order
    ) -> None:
        t = Ticket(order_id=order.id, seat_id=seat.id, status=TicketStatus.VALID)
        db.add(t)
        db.commit()

        assert db.execute(self.UPDATE, {"id": t.id}).rowcount == 1

    def test_second_validation_affects_no_row(
        self, db: Session, seat: Seat, order: Order
    ) -> None:
        t = Ticket(order_id=order.id, seat_id=seat.id, status=TicketStatus.VALID)
        db.add(t)
        db.commit()

        db.execute(self.UPDATE, {"id": t.id})
        assert db.execute(self.UPDATE, {"id": t.id}).rowcount == 0

    def test_cancelled_ticket_cannot_be_validated(
        self, db: Session, seat: Seat, order: Order
    ) -> None:
        t = Ticket(order_id=order.id, seat_id=seat.id,
                   status=TicketStatus.CANCELLED)
        db.add(t)
        db.commit()

        assert db.execute(self.UPDATE, {"id": t.id}).rowcount == 0


class TestReferentialIntegrity:
    def test_gate_cannot_point_to_missing_event(self, db: Session) -> None:
        """Sem esta chave, todo ingresso legítimo viraria 'evento errado'."""
        from app.models import Role
        from app.security import hash_password

        db.add(User(name="Portaria Fantasma", email="fantasma@cinerini.com.br",
                    password_hash=hash_password("x"), role=Role.GATE,
                    gate_event_id=999_999_999))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_public_ticket_code_is_unique(
        self, db: Session, showing: Showing, order: Order
    ) -> None:
        assentos = db.scalars(
            select(Seat).where(Seat.showing_id == showing.id).limit(2)
        ).all()

        primeiro = Ticket(order_id=order.id, seat_id=assentos[0].id)
        db.add(primeiro)
        db.commit()

        db.add(Ticket(order_id=order.id, seat_id=assentos[1].id,
                      jti=primeiro.jti))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
