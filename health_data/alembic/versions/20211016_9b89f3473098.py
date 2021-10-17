"""Add notes fields for temperature and weight

Revision ID: 9b89f3473098
Revises: 3a502a033702
Create Date: 2021-10-16 22:34:39.513467

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b89f3473098'
down_revision = '3a502a033702'
branch_labels = None
depends_on = None

def upgrade():

    with op.batch_alter_table('temperature', schema=None) as batch_op:
        batch_op.add_column(sa.Column('notes_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_temperature_notes_id_note'), 'note', ['notes_id'], ['id'])

    with op.batch_alter_table('weight', schema=None) as batch_op:
        batch_op.add_column(sa.Column('notes_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_weight_notes_id_note'), 'note', ['notes_id'], ['id'])

def downgrade():

    with op.batch_alter_table('weight', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_weight_notes_id_note'), type_='foreignkey')
        batch_op.drop_column('notes_id')

    with op.batch_alter_table('temperature', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_temperature_notes_id_note'), type_='foreignkey')
        batch_op.drop_column('notes_id')
