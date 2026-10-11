"""device monitoring: last_seen, status, thresholds, unique readings

Revision ID: 7b2e91c4d5a0
Revises: 3c22ffdd6bb6
Create Date: 2026-10-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7b2e91c4d5a0'
down_revision: Union[str, Sequence[str], None] = '3c22ffdd6bb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('devices', sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True))
    op.add_column('devices', sa.Column('status', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('devices', sa.Column('temp_min', sa.Float(), nullable=True))
    op.add_column('devices', sa.Column('temp_max', sa.Float(), nullable=True))
    op.add_column('devices', sa.Column('hum_min', sa.Float(), nullable=True))
    op.add_column('devices', sa.Column('hum_max', sa.Float(), nullable=True))

    # Время последнего контакта — по уже накопленным данным.
    op.execute("""
        UPDATE devices d SET last_seen = x.ts
        FROM (SELECT device_id, max(timestamp) AS ts FROM device_data GROUP BY device_id) x
        WHERE x.device_id = d.id
    """)

    # Перед уникальным индексом убираем повторы с одинаковым временем.
    op.execute("""
        DELETE FROM device_data a
        USING device_data b
        WHERE a.device_id = b.device_id AND a.timestamp = b.timestamp AND a.id > b.id
    """)
    op.create_index('ix_device_data_device_timestamp', 'device_data', ['device_id', 'timestamp'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_device_data_device_timestamp', table_name='device_data')
    for column in ('hum_max', 'hum_min', 'temp_max', 'temp_min', 'status', 'last_seen'):
        op.drop_column('devices', column)
