"""Set default for modified_date and symptomtype.entry_date to CURRENT_TIMESTAMP

Revision ID: 0d50468feaf8
Revises: cc369c0efc37
Create Date: 2020-04-27 20:43:41.131903

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '0d50468feaf8'
down_revision = 'cc369c0efc37'
branch_labels = None
depends_on = None

def upgrade():

    for table in 'note','period','symptom','symptomtype','temperature','weight':
        with op.batch_alter_table(table, schema=None,recreate='always') as batch_op:
            batch_op.alter_column('modified_date',
                                  server_default=func.now())

    with op.batch_alter_table('symptomtype',schema=None,recreate='always') as batch_op:
        batch_op.alter_column('entry_date',
                              server_default=func.now())

def downgrade():

    for table in 'note','period','symptom','symptomtype','temperature','weight':
        with op.batch_alter_table(table, schema=None,recreate='always') as batch_op:
            batch_op.alter_column('modified_date', server_default=None)

    with op.batch_alter_table('symptomtype',schema=None,recreate='always') as batch_op:
        batch_op.alter_column('entry_date',
                              server_default=None)
