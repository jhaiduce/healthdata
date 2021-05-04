"""Add height column to weight table

Revision ID: 1629d163150c
Revises: e2aa55c58b9d
Create Date: 2021-05-04 10:13:16.029739

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1629d163150c'
down_revision = 'e2aa55c58b9d'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('weight', schema=None) as batch_op:
        batch_op.add_column(sa.Column('height', sa.Float(), nullable=True))

def downgrade():
    with op.batch_alter_table('weight', schema=None) as batch_op:
        batch_op.drop_column('height')
