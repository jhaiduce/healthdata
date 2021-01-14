"""Added tables for recording weights of absorbent garments before and after use

Revision ID: f3d8ece8285e
Revises: da6f9cd31058
Create Date: 2021-01-14 16:22:48.160550

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3d8ece8285e'
down_revision = 'da6f9cd31058'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('absorbent_garments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_absorbent_garments')),
    mysql_encrypted='yes'
    )
    op.create_table('absorbent_weights',
    sa.Column('entry_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('modified_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time_before', sa.DateTime(), nullable=True),
    sa.Column('time_after', sa.DateTime(), nullable=True),
    sa.Column('garment_id', sa.Integer(), nullable=True),
    sa.Column('weight_before', sa.Float(), nullable=True),
    sa.Column('weight_after', sa.Float(), nullable=True),
    sa.Column('notes_id', sa.Integer(), nullable=True),
    sa.Column('blood_observed', sa.Boolean(), nullable=True),
    sa.Column('person_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['garment_id'], ['absorbent_garments.id'], name=op.f('fk_absorbent_weights_garment_id_absorbent_garments')),
    sa.ForeignKeyConstraint(['id'], ['record.id'], name=op.f('fk_absorbent_weights_id_record')),
    sa.ForeignKeyConstraint(['notes_id'], ['note.id'], name=op.f('fk_absorbent_weights_notes_id_note')),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], name='fk_absorbent_weights_person_id'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_absorbent_weights')),
    mysql_encrypted='yes'
    )

def downgrade():
    op.drop_table('absorbent_weights')
    op.drop_table('absorbent_garments')
