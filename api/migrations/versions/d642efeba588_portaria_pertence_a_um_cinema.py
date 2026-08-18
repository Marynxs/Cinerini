"""portaria pertence a um cinema

Revision ID: d642efeba588
Revises: c45d37a00d2e
Create Date: 2026-08-17 22:37:28.213608

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd642efeba588'
down_revision: Union[str, Sequence[str], None] = 'c45d37a00d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('gate_venue_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_users_gate_venue_id'), 'users', ['gate_venue_id'])

    # Nomeada, e não deixada a cargo do autogenerate: sem nome explícito o
    # Alembic grava `None`, e a constraint fica impossível de remover depois
    # sem descobrir o nome que o Postgres inventou.
    op.create_foreign_key('fk_users_gate_venue', 'users', 'venues',
                          ['gate_venue_id'], ['id'], ondelete='SET NULL')

    # A portaria que já atendia uma sessão passa a pertencer ao cinema dessa
    # sessão. Sem a conversão, quem tinha portaria montada perderia o escopo
    # e não conseguiria escolher turno nenhum.
    op.execute("""
        UPDATE users u
        SET gate_venue_id = (
            SELECT r.venue_id
            FROM showings s JOIN rooms r ON r.id = s.room_id
            WHERE s.id = u.gate_showing_id
        )
        WHERE u.gate_showing_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_constraint('fk_users_gate_venue', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_gate_venue_id'), table_name='users')
    op.drop_column('users', 'gate_venue_id')
