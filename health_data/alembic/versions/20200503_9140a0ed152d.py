"""Added a relationship between the person table and tables based on the IndividualRecord class

Revision ID: 9140a0ed152d
Revises: 0d50468feaf8
Create Date: 2020-05-03 17:08:27.096172

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9140a0ed152d'
down_revision = '0d50468feaf8'
branch_labels = None
depends_on = None

def upgrade():

    with op.batch_alter_table('period', schema=None) as batch_op:
        batch_op.add_column(sa.Column('person_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_period_person_id', 'person', ['person_id'], ['id'])

    with op.batch_alter_table('symptom', schema=None) as batch_op:
        batch_op.add_column(sa.Column('person_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_symptom_person_id', 'person', ['person_id'], ['id'])

    with op.batch_alter_table('temperature', schema=None) as batch_op:
        batch_op.add_column(sa.Column('person_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_temperature_person_id', 'person', ['person_id'], ['id'])

    with op.batch_alter_table('weight', schema=None) as batch_op:
        batch_op.add_column(sa.Column('person_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_weight_person_id', 'person', ['person_id'], ['id'])

def downgrade():

    with op.batch_alter_table('weight', schema=None) as batch_op:
        batch_op.drop_constraint('fk_weight_person_id', type_='foreignkey')
        batch_op.drop_column('person_id')

    with op.batch_alter_table('temperature', schema=None) as batch_op:
        batch_op.drop_constraint('fk_temperature_person_id', type_='foreignkey')
        batch_op.drop_column('person_id')

    with op.batch_alter_table('symptom', schema=None) as batch_op:
        batch_op.drop_constraint('fk_symptom_person_id', type_='foreignkey')
        batch_op.drop_column('person_id')

    with op.batch_alter_table('period', schema=None) as batch_op:
        batch_op.drop_constraint('fk_period_person_id', type_='foreignkey')
        batch_op.drop_column('person_id')
