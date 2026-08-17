"""portaria vinculada a sessao

Revision ID: 82ec8644b13c
Revises: ec9821a0ac58
Create Date: 2026-08-17 19:46:02.880550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82ec8644b13c'
down_revision: Union[str, Sequence[str], None] = 'ec9821a0ac58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('gate_showing_id', sa.Integer(), nullable=True))

    # A portaria que atendia um filme passa a atender a primeira exibição
    # dele. Sem esta conversão, quem já tinha portaria montada acordaria com
    # ela desvinculada — e a única pista seria a recusa de todo ingresso.
    op.execute("""
        UPDATE users u
        SET gate_showing_id = (
            SELECT s.id FROM showings s
            WHERE s.event_id = u.gate_event_id
            ORDER BY s.starts_at
            LIMIT 1
        )
        WHERE u.gate_event_id IS NOT NULL
    """)

    op.drop_constraint(op.f('fk_users_gate_event'), 'users', type_='foreignkey')
    op.create_foreign_key('fk_users_gate_showing', 'users', 'showings', ['gate_showing_id'], ['id'], ondelete='SET NULL', use_alter=True)
    op.drop_column('users', 'gate_event_id')


def downgrade() -> None:
    op.add_column('users', sa.Column('gate_event_id', sa.INTEGER(), autoincrement=False, nullable=True))

    # Caminho de volta: a exibição sabe de que evento é, então a conversão
    # inversa não perde nada além da precisão do horário.
    op.execute("""
        UPDATE users u
        SET gate_event_id = (
            SELECT s.event_id FROM showings s WHERE s.id = u.gate_showing_id
        )
        WHERE u.gate_showing_id IS NOT NULL
    """)

    op.drop_constraint('fk_users_gate_showing', 'users', type_='foreignkey')
    op.create_foreign_key(op.f('fk_users_gate_event'), 'users', 'events', ['gate_event_id'], ['id'], ondelete='SET NULL')
    op.drop_column('users', 'gate_showing_id')
