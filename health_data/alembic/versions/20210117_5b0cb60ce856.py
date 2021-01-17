"""Remove time column from menstrual_cup_fill table

Revision ID: 5b0cb60ce856
Revises: 04578f0d6e1d
Create Date: 2021-01-17 15:40:40.312790

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b0cb60ce856'
down_revision = '04578f0d6e1d'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('menstrual_cup_fill', schema=None) as batch_op:
        batch_op.drop_column('time')

def downgrade():
    with op.batch_alter_table('menstrual_cup_fill', schema=None) as batch_op:
        batch_op.add_column(sa.Column('time', sa.DATETIME(), nullable=True))
