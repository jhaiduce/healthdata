"""Added notes column to Symptom table

Revision ID: 50f4523b1870
Revises: 9140a0ed152d
Create Date: 2020-07-03 09:26:08.264997

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '50f4523b1870'
down_revision = '9140a0ed152d'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('symptom', schema=None) as batch_op:
        batch_op.add_column(sa.Column('notes_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_symptom_notes_id_note'), 'note', ['notes_id'], ['id'])

def downgrade():
    with op.batch_alter_table('symptom', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_symptom_notes_id_note'), type_='foreignkey')
        batch_op.drop_column('notes_id')
