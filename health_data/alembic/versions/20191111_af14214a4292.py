"""Added columns to the period table and renamed the intensity column to period_intensity

Revision ID: af14214a4292
Revises: a4341b6bb592
Create Date: 2019-11-11 17:07:06.777369

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af14214a4292'
down_revision = 'a4341b6bb592'
branch_labels = None
depends_on = None

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('period', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cervical_fluid_character', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('notes_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('period_intensity', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('temperature_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_period_temperature_id_temperature'), 'temperature', ['temperature_id'], ['id'])
        batch_op.create_foreign_key(batch_op.f('fk_period_notes_id_note'), 'note', ['notes_id'], ['id'])
        batch_op.drop_column('intensity')

    # ### end Alembic commands ###

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('period', schema=None) as batch_op:
        batch_op.add_column(sa.Column('intensity', sa.FLOAT(), nullable=True))
        batch_op.drop_constraint(batch_op.f('fk_period_notes_id_note'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_period_temperature_id_temperature'), type_='foreignkey')
        batch_op.drop_column('temperature_id')
        batch_op.drop_column('period_intensity')
        batch_op.drop_column('notes_id')
        batch_op.drop_column('cervical_fluid_character')

    # ### end Alembic commands ###
