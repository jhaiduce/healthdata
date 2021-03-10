"""Add tables to store blood pressure and heart rate

Revision ID: a3dc1b53c319
Revises: 5b0cb60ce856
Create Date: 2021-03-09 19:27:05.276704

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3dc1b53c319'
down_revision = '5b0cb60ce856'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('heart_rate',
    sa.Column('entry_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('modified_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=True),
    sa.Column('utcoffset', sa.Integer(), nullable=True),
    sa.Column('rate', sa.Float(), nullable=True),
    sa.Column('person_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id'], ['record.id'], name=op.f('fk_heart_rate_id_record')),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], name='fk_heart_rate_person_id'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_heart_rate')),
    mysql_encrypted='yes'
    )
    op.create_table('blood_pressure',
    sa.Column('entry_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('modified_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=True),
    sa.Column('utcoffset', sa.Integer(), nullable=True),
    sa.Column('systolic', sa.Float(), nullable=True),
    sa.Column('diastolic', sa.Float(), nullable=True),
    sa.Column('heart_rate_id', sa.Integer(), nullable=True),
    sa.Column('person_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['heart_rate_id'], ['heart_rate.id'], name=op.f('fk_blood_pressure_heart_rate_id_heart_rate')),
    sa.ForeignKeyConstraint(['id'], ['record.id'], name=op.f('fk_blood_pressure_id_record')),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], name='fk_blood_pressure_person_id'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_blood_pressure')),
    mysql_encrypted='yes'
    )

def downgrade():
    op.drop_table('blood_pressure')
    op.drop_table('heart_rate')
