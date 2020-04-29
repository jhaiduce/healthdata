"""Replace created/modified columns of record table with created/modified columns in individual record type tables

Revision ID: cc369c0efc37
Revises: af14214a4292
Create Date: 2020-03-01 13:06:08.014277

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cc369c0efc37'
down_revision = 'af14214a4292'
branch_labels = None
depends_on = None

from sqlalchemy import (
    Column,
    Index,
    Integer,
    Text,
    String,
    DateTime,
    Float,
    ForeignKey,
    Sequence,
    Date
)
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.ext.declarative import declared_attr

Base = declarative_base()

class Record(Base):

    __tablename__='record'
    id = Column(Integer, Sequence('record_seq'), primary_key=True)
    record_entry_date = Column('entry_date',DateTime)
    record_modified_date = Column('modified_date',DateTime)
    record_type = Column(String(255))

class Temperature(Record):
    __tablename__='temperature'
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    entry_date = Column(DateTime)
    modified_date = Column(DateTime)

class Period(Record):
    __tablename__='period'
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    entry_date = Column(DateTime)
    modified_date = Column(DateTime)

def upgrade():

    bind=op.get_bind()

    if bind.engine.name=='sqlite':
        recreate='always'
    else:
        recreate='auto'

    with op.batch_alter_table('note', schema=None,recreate=recreate) as batch_op:
        batch_op.add_column(sa.Column('entry_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))
        batch_op.add_column(sa.Column('modified_date', sa.DateTime(), nullable=True))

    with op.batch_alter_table('period', schema=None,recreate=recreate) as batch_op:
        batch_op.add_column(sa.Column('entry_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))
        batch_op.add_column(sa.Column('modified_date', sa.DateTime(), nullable=True))

    with op.batch_alter_table('symptom', schema=None,recreate=recreate) as batch_op:
        batch_op.add_column(sa.Column('entry_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))
        batch_op.add_column(sa.Column('modified_date', sa.DateTime(), nullable=True))

    with op.batch_alter_table('temperature', schema=None,recreate=recreate) as batch_op:
        batch_op.add_column(sa.Column('entry_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))
        batch_op.add_column(sa.Column('modified_date', sa.DateTime(), nullable=True))

    with op.batch_alter_table('weight', schema=None,recreate=recreate) as batch_op:
        batch_op.add_column(sa.Column('entry_date', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))
        batch_op.add_column(sa.Column('modified_date', sa.DateTime(), nullable=True))

    session=orm.Session(bind=op.get_bind())
    for cls in Period, Temperature:
        objects=session.query(cls)
        for obj in objects:
            obj.entry_date=obj.record_entry_date
            obj.modified_date=obj.record_modified_date

    session.commit()

    with op.batch_alter_table('record', schema=None) as batch_op:
        batch_op.drop_constraint('fk_user_id', type_='foreignkey')
        batch_op.drop_column('person')
        batch_op.drop_column('entry_date')
        batch_op.drop_column('modified_date')

def downgrade():

    with op.batch_alter_table('record', schema=None) as batch_op:
        batch_op.add_column(sa.Column('modified_date', sa.DATETIME(), nullable=True))
        batch_op.add_column(sa.Column('entry_date', sa.DATETIME(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))
        batch_op.add_column(sa.Column('person', sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key('fk_user_id', 'user', ['person'], ['id'])

    session=orm.Session(bind=op.get_bind())
    for cls in Period, Temperature:
        objects=session.query(cls)
        for obj in objects:
            obj.record_entry_date=obj.entry_date
            obj.record_modified_date=obj.modified_date

    session.commit()

    with op.batch_alter_table('weight', schema=None) as batch_op:
        batch_op.drop_column('modified_date')
        batch_op.drop_column('entry_date')

    with op.batch_alter_table('temperature', schema=None) as batch_op:
        batch_op.drop_column('modified_date')
        batch_op.drop_column('entry_date')

    with op.batch_alter_table('symptom', schema=None) as batch_op:
        batch_op.drop_column('modified_date')
        batch_op.drop_column('entry_date')

    with op.batch_alter_table('period', schema=None) as batch_op:
        batch_op.drop_column('modified_date')
        batch_op.drop_column('entry_date')

    with op.batch_alter_table('note', schema=None) as batch_op:
        batch_op.drop_column('modified_date')
        batch_op.drop_column('entry_date')
