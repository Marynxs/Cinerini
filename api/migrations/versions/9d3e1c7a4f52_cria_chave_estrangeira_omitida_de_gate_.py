"""cria chave estrangeira omitida de gate_event

users.gate_event_id foi declarada com use_alter na migration inicial. Esse
parâmetro faz o Alembic omitir a chave do CREATE TABLE para resolver a
referência circular entre users e events, mas o ALTER TABLE correspondente
nunca foi emitido, e a constraint não chegou a existir no banco.

Sem ela, nada impedia gravar um usuário de portaria apontando para um evento
inexistente, e a distinção entre "evento errado" e "inválido" perderia base.

Revision ID: 9d3e1c7a4f52
Revises: ef7a59ce5045
Create Date: 2026-08-15 14:49:00.325716

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d3e1c7a4f52'
down_revision: Union[str, Sequence[str], None] = 'ef7a59ce5045'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_foreign_key(
        'fk_users_gate_event', 'users', 'events', ['gate_event_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_users_gate_event', 'users', type_='foreignkey')
