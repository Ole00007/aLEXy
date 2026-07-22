"""add webhook subscriptions and deliveries

Revision ID: d1e2f3a4b5c6
Revises: 8b1c2d3e4f5a
Create Date: 2026-07-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = '8b1c2d3e4f5a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('events', sa.JSON(), nullable=False),
        sa.Column('secret', sa.String(length=64), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('http_status_code', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['subscription_id'], ['webhook_subscriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('webhook_deliveries')
    op.drop_table('webhook_subscriptions')
