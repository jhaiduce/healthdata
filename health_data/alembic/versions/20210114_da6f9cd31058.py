"""Encrypt record tables

Revision ID: da6f9cd31058
Revises: c5c1c8acef40
Create Date: 2021-01-14 10:22:26.922475

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'da6f9cd31058'
down_revision = 'c5c1c8acef40'
branch_labels = None
depends_on = None

def upgrade():

    conn=op.get_bind()

    if conn.dialect.name=='mysql':

        for tablename in 'record','note','temperature','weight','symptomtype', \
            'symptom','period','menstrual_cup_fill':
            conn.execute("ALTER TABLE {} ENCRYPTED='YES'".format(tablename))

def downgrade():

    conn=op.get_bind()

    if conn.dialect.name=='mysql':

        for tablename in 'record','note','temperature','weight','symptomtype','symptom','period','menstrual_cup_fill':
            conn.execute("ALTER TABLE {} ENCRYPTED='NO'".format(tablename))
