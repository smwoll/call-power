"""target_office location and type

Revision ID: 4f2d9aae4765
Revises: d024eda790a3
Create Date: 2018-04-26 10:42:20.052516

"""

# revision identifiers, used by Alembic.
revision = '4f2d9aae4765'
down_revision = 'd024eda790a3'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('campaign_target_office', schema=None) as batch_op:
        batch_op.add_column(sa.Column('latlon', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('type', sa.String(length=100), nullable=True))
        batch_op.drop_column('location')
    ### end Alembic commands ###

def downgrade():
    with op.batch_alter_table('campaign_target_office', schema=None) as batch_op:
        batch_op.add_column(sa.Column('location', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
        batch_op.drop_column('type')
        batch_op.drop_column('latlon')

    ### end Alembic commands ###
