"""Add an LH surge column to the period table

Revision ID: 3a502a033702
Revises: 1629d163150c
Create Date: 2021-09-23 19:45:12.394111

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a502a033702'
down_revision = '1629d163150c'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('period', schema=None) as batch_op:
        batch_op.add_column(sa.Column('lh_surge', sa.Integer(), nullable=True))

def downgrade():
    with op.batch_alter_table('period', schema=None) as batch_op:
        batch_op.drop_column('lh_surge')
