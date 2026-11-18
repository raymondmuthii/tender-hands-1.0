"""link donations to the recurring donation that created them

Revision ID: 9c1f2b7d84aa
Revises: 84d01880d7cf
Create Date: 2026-11-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c1f2b7d84aa'
down_revision = '84d01880d7cf'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('donations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('recurring_donation_id', sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_donations_recurring_donation_id'),
            ['recurring_donation_id'],
            unique=False,
        )
        batch_op.create_foreign_key(
            'fk_donations_recurring_donation_id',
            'recurring_donations',
            ['recurring_donation_id'],
            ['id'],
        )


def downgrade():
    with op.batch_alter_table('donations', schema=None) as batch_op:
        batch_op.drop_constraint('fk_donations_recurring_donation_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_donations_recurring_donation_id'))
        batch_op.drop_column('recurring_donation_id')
