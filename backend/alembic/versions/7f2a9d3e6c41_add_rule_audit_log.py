"""add_rule_audit_log

Revision ID: 7f2a9d3e6c41
Revises: 3b1e79edfedf
Create Date: 2026-07-10 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f2a9d3e6c41'
down_revision: Union[str, None] = '3b1e79edfedf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rule_audit_log',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('commission_rule_id', sa.Integer(), sa.ForeignKey('commission_rules.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('field', sa.String(length=100), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('edited_by', sa.String(length=100), nullable=False, server_default='User'),
        sa.Column('edited_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('rule_audit_log')
