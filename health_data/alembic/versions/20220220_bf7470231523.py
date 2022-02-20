"""Add body measurements table

Revision ID: bf7470231523
Revises: 9b89f3473098
Create Date: 2022-02-20 12:00:19.983251

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bf7470231523'
down_revision = '9b89f3473098'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('body_measurements',
    sa.Column('entry_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('modified_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=True),
    sa.Column('utcoffset', sa.Integer(), nullable=True),
    sa.Column('bust', sa.Float(), nullable=True),
    sa.Column('under_ribcage', sa.Float(), nullable=True),
    sa.Column('fullest_belly', sa.Float(), nullable=True),
    sa.Column('waist', sa.Float(), nullable=True),
    sa.Column('hips', sa.Float(), nullable=True),
    sa.Column('notes_id', sa.Integer(), nullable=True),
    sa.Column('person_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id'], ['record.id'], name=op.f('fk_body_measurements_id_record')),
    sa.ForeignKeyConstraint(['notes_id'], ['note.id'], name=op.f('fk_body_measurements_notes_id_note')),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], name='fk_body_measurements_person_id'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_body_measurements')),
    mysql_encrypted='yes'
    )

def downgrade():
    op.drop_table('body_measurements')
