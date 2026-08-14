"""normaliza sala em tabela propria

Revision ID: a8c7bf3f28f7
Revises: b0b64e3d9473
Create Date: 2026-08-14 18:00:25.855054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8c7bf3f28f7'
down_revision: Union[str, Sequence[str], None] = 'b0b64e3d9473'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('rooms',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('venue', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=60), nullable=False),
    sa.Column('rows', sa.Integer(), nullable=False),
    sa.Column('seats_per_row', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('venue', 'name', name='uq_room_no_local')
    )
    op.create_index(op.f('ix_rooms_venue'), 'rooms', ['venue'], unique=False)
    op.drop_column('events', 'venue')
    op.add_column('showings', sa.Column('room_id', sa.Integer(), nullable=False))
    op.create_index(op.f('ix_showings_room_id'), 'showings', ['room_id'], unique=False)
    op.create_foreign_key(
        'fk_showings_room', 'showings', 'rooms', ['room_id'], ['id'],
        ondelete='RESTRICT',
    )
    op.drop_column('showings', 'room')
    op.drop_column('showings', 'seats_per_row')
    op.drop_column('showings', 'rows')

    # O autogenerate propôs recriar fk_users_gate_event aqui. É falso
    # positivo: ele não reconhece a chave declarada com use_alter como já
    # existente. Recriá-la falharia com constraint duplicada.


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('showings', sa.Column('rows', sa.INTEGER(), autoincrement=False, nullable=False))
    op.add_column('showings', sa.Column('seats_per_row', sa.INTEGER(), autoincrement=False, nullable=False))
    op.add_column('showings', sa.Column('room', sa.VARCHAR(length=60), autoincrement=False, nullable=False))
    op.drop_constraint('fk_showings_room', 'showings', type_='foreignkey')
    op.drop_index(op.f('ix_showings_room_id'), table_name='showings')
    op.drop_column('showings', 'room_id')
    op.add_column('events', sa.Column('venue', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
    op.drop_index(op.f('ix_rooms_venue'), table_name='rooms')
    op.drop_table('rooms')
