"""Move common submodule/moduleversion columns to new module_details table

Revision ID: 47e45e505e22
Revises: a36ffbb6580e
Create Date: 2022-07-04 16:52:55.547319

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '47e45e505e22'
down_revision = 'a36ffbb6580e'
branch_labels = None
depends_on = None

def migrate_data_to_module_details(c, source_table):
    """Migrate readme_content and module_details columns from source table to rows in module_details table."""
    # Iterate over all rows of source table, extract readme_content and module_details,
    # create row in module_details table and update module_details foreign key ID in source table
    res = c.execute(f"""SELECT id, readme_content, module_details FROM {source_table}""")
    for row in res:

        source_id, readme_content, module_details = row
        # Insert row into module_details
        insert_res = c.execute(
            sa.sql.text("""
                INSERT INTO module_details(readme_content, terraform_docs)
                VALUES(:readme_content, :module_details)
            """),
            readme_content=readme_content, module_details=module_details)
        module_details_id = insert_res.inserted_primary_key[0]

        # Update module_version with new inserted ID
        c.execute(sa.sql.text(f"""UPDATE {source_table} SET module_details_id=:module_details_id WHERE id=:source_id"""),
                  module_details_id=module_details_id, source_id=source_id)


def upgrade():
    # Create new table for module_details
    op.create_table(
        'module_details',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('readme_content', sa.LargeBinary(length=16777215).with_variant(mysql.MEDIUMBLOB(), 'mysql'), nullable=True),
        sa.Column('terraform_docs', sa.LargeBinary(length=16777215).with_variant(mysql.MEDIUMBLOB(), 'mysql'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    c = op.get_bind()

    # Add column to module_version table for link to module details table
    with op.batch_alter_table('module_version', schema=None) as batch_op:
        batch_op.add_column(sa.Column('module_details_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_module_version_module_details_id_module_details_id', 'module_details', ['module_details_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    # Migrate data from module_version table
    migrate_data_to_module_details(c, 'module_version')

    # Remove old columns from module_version table
    with op.batch_alter_table('module_version', schema=None) as batch_op:
        batch_op.drop_column('readme_content')
        batch_op.drop_column('module_details')

    # Add column to submodule table for link to module details table - initially set
    # nullable to all for None value after adding colummn
    with op.batch_alter_table('submodule', schema=None) as batch_op:
        batch_op.add_column(sa.Column('module_details_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_submodule_module_details_id_module_details_id', 'module_details', ['module_details_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    # Migrate data from submodule table
    migrate_data_to_module_details(c, 'submodule')

    # Remove old columns from submodule table
    with op.batch_alter_table('submodule', schema=None) as batch_op:
        batch_op.drop_column('readme_content')
        batch_op.drop_column('module_details')


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('submodule', schema=None) as batch_op:
        batch_op.add_column(sa.Column('module_details', sa.BLOB().with_variant(sa.LargeBinary(), "postgresql"), nullable=True))
        batch_op.add_column(sa.Column('readme_content', sa.BLOB().with_variant(sa.LargeBinary(), "postgresql"), nullable=True))

    c = op.get_bind()

    c.execute(sa.sql.text("""
        UPDATE submodule
        SET
            module_details=(SELECT terraform_docs FROM module_details WHERE id=submodule.id),
            readme_content=(SELECT readme_content FROM module_details WHERE id=submodule.id)
    """))

    with op.batch_alter_table('submodule', schema=None) as batch_op:
        batch_op.drop_constraint('fk_submodule_module_details_id_module_details_id', type_='foreignkey')
        batch_op.drop_column('module_details_id')

    with op.batch_alter_table('module_version', schema=None) as batch_op:
        batch_op.add_column(sa.Column('module_details', sa.BLOB().with_variant(sa.LargeBinary(), "postgresql"), nullable=True))
        batch_op.add_column(sa.Column('readme_content', sa.BLOB().with_variant(sa.LargeBinary(), "postgresql"), nullable=True))

    c.execute(sa.sql.text("""
        UPDATE module_version
        SET
            module_details=(SELECT terraform_docs FROM module_details WHERE id=module_version.id),
            readme_content=(SELECT readme_content FROM module_details WHERE id=module_version.id)
    """))

    with op.batch_alter_table('module_version', schema=None) as batch_op:
        batch_op.drop_constraint('fk_module_version_module_details_id_module_details_id', type_='foreignkey')
        batch_op.drop_column('module_details_id')

    op.drop_table('module_details')
