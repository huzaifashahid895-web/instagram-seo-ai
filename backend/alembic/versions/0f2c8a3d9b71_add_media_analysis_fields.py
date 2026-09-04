"""add_media_analysis_fields

Revision ID: 0f2c8a3d9b71
Revises: d7018b495f15
Create Date: 2026-09-03 06:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0f2c8a3d9b71"
down_revision: Union[str, Sequence[str], None] = "d7018b495f15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("content_analysis", sa.Column("file_size", sa.Integer(), nullable=True))
    op.add_column("content_analysis", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("content_analysis", sa.Column("height", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("content_analysis", "height")
    op.drop_column("content_analysis", "width")
    op.drop_column("content_analysis", "file_size")
