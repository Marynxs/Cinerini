"""Prepara a corrida pelo mesmo assento: N clientes e uma poltrona livre.

Roda dentro do contêiner da API, contra o banco que o teste vai usar:

    python -m loadtest.preparar 500 > corrida.json

Os tokens são emitidos direto com a chave do ambiente, e não pelo login: o
limite de 60 logins por IP a cada 5 minutos barraria a preparação, e o que
se mede é a reserva, não a autenticação. Os clientes ficam no banco; o seed
com --reset os remove.
"""

import json
import sys

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Role, Seat, Showing, Ticket, TicketStatus, User
from app.security import create_access_token, hash_password


def main(quantidade: int) -> None:
    with SessionLocal() as db:
        # Sessão futura com poltrona sem ingresso vivo. Escolhida pelo banco,
        # e não fixa, para o teste rodar sobre qualquer seed.
        ocupada = (
            select(Ticket.seat_id).where(Ticket.status != TicketStatus.CANCELLED)
        )
        assento = db.scalar(
            select(Seat)
            .join(Showing, Seat.showing_id == Showing.id)
            .where(Showing.starts_at > func.now(), Seat.id.not_in(ocupada))
            .order_by(Showing.starts_at, Seat.id)
            .limit(1)
        )
        if assento is None:
            sys.exit("Nenhuma poltrona livre em sessão futura. Rode o seed.")

        # Um hash só para todos: bcrypt custa centenas de milissegundos, e a
        # senha não é usada, porque o token é emitido aqui.
        senha = hash_password("carga-nao-usada")
        clientes = [
            User(name=f"Carga {i}", email=f"carga{i}@cinerini.com.br",
                 password_hash=senha, role=Role.CUSTOMER)
            for i in range(quantidade)
        ]
        db.add_all(clientes)
        db.commit()

        json.dump({
            "showing_id": assento.showing_id,
            "seat_id": assento.id,
            "tokens": [create_access_token(c.id, c.role) for c in clientes],
        }, sys.stdout)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 500)
