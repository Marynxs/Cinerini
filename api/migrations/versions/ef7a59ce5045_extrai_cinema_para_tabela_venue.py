"""extrai cinema para tabela venue

Revision ID: ef7a59ce5045
Revises: a8c7bf3f28f7
Create Date: 2026-08-15 14:22:41.571143

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef7a59ce5045'
down_revision: Union[str, Sequence[str], None] = 'a8c7bf3f28f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('venues',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('city', sa.String(length=120), nullable=False),
    sa.Column('state', sa.String(length=2), nullable=False),
    sa.Column('address', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'city', name='uq_venue_na_cidade')
    )
    op.create_index(op.f('ix_venues_city'), 'venues', ['city'], unique=False)
    op.add_column('rooms', sa.Column('venue_id', sa.Integer(), nullable=False))
    op.drop_index(op.f('ix_rooms_venue'), table_name='rooms')
    op.drop_constraint(op.f('uq_room_no_local'), 'rooms', type_='unique')
    op.create_index(op.f('ix_rooms_venue_id'), 'rooms', ['venue_id'], unique=False)
    op.create_unique_constraint('uq_room_no_venue', 'rooms', ['venue_id', 'name'])
    op.create_foreign_key(
        'fk_rooms_venue', 'rooms', 'venues', ['venue_id'], ['id'],
        ondelete='RESTRICT',
    )
    op.drop_column('rooms', 'venue')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('rooms', sa.Column('venue', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
    op.drop_constraint('fk_rooms_venue', 'rooms', type_='foreignkey')
    op.drop_constraint('uq_room_no_venue', 'rooms', type_='unique')
    op.drop_index(op.f('ix_rooms_venue_id'), table_name='rooms')
    op.create_unique_constraint(op.f('uq_room_no_local'), 'rooms', ['venue', 'name'], postgresql_nulls_not_distinct=False)
    op.create_index(op.f('ix_rooms_venue'), 'rooms', ['venue'], unique=False)
    op.drop_column('rooms', 'venue_id')
    op.drop_index(op.f('ix_venues_city'), table_name='venues')
    op.drop_table('venues')
