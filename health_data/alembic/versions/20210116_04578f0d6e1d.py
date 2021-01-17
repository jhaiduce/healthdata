"""Added insertion_time and removal_time fields to MenstrualCupFill

Revision ID: 04578f0d6e1d
Revises: f3d8ece8285e
Create Date: 2021-01-16 15:46:58.811583

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '04578f0d6e1d'
down_revision = 'f3d8ece8285e'
branch_labels = None
depends_on = None

def upgrade():
    conn=op.get_bind()

    with op.batch_alter_table('menstrual_cup_fill', schema=None) as batch_op:

        batch_op.add_column(sa.Column('insertion_time', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('removal_time', sa.DateTime(), nullable=True, server_default=sa.text('time') if conn.dialect.name!='sqlite' else None,server_onupdate=sa.text('time')))

    menstrual_cup_fill=sa.table(
        'menstrual_cup_fill',
        sa.column('removal_time',sa.DateTime()),
        sa.column('time',sa.DateTime())
    )

    result = conn.execute(
        menstrual_cup_fill.update(
        ).values(
            removal_time=sa.text('time')
        )
    )

def downgrade():
    
    with op.batch_alter_table('menstrual_cup_fill', schema=None) as batch_op:
        batch_op.drop_column('removal_time')
        batch_op.drop_column('insertion_time')
