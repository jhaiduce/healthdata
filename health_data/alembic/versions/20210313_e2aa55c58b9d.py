"""Add columns for TOTP shared secret and last used OTP

Revision ID: e2aa55c58b9d
Revises: a3dc1b53c319
Create Date: 2021-03-13 12:52:44.840358

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2aa55c58b9d'
down_revision = 'a3dc1b53c319'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_otp_hash', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('otp_secret', sa.String(length=32), nullable=True))

def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('otp_secret')
        batch_op.drop_column('last_otp_hash')
