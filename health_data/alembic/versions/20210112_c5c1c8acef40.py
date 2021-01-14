"""Added table for storing records of menstrual cup fill

Revision ID: c5c1c8acef40
Revises: 50f4523b1870
Create Date: 2021-01-12 18:49:34.951223

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5c1c8acef40'
down_revision = '50f4523b1870'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('menstrual_cup_fill',
    sa.Column('entry_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('modified_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=True),
    sa.Column('fill', sa.Float(), nullable=True),
    sa.Column('notes_id', sa.Integer(), nullable=True),
    sa.Column('person_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id'], ['record.id'], name=op.f('fk_menstrual_cup_fill_id_record')),
    sa.ForeignKeyConstraint(['notes_id'], ['note.id'], name=op.f('fk_menstrual_cup_fill_notes_id_note')),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], name='fk_menstrual_cup_fill_person_id'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_menstrual_cup_fill'))
    )

def downgrade():
    op.drop_table('menstrual_cup_fill')
