from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from ai_tutor.models import metadata


def test_migration_matches_models_and_roundtrips(database):
    config = Config("alembic.ini")
    with database.begin() as conn:
        assert compare_metadata(MigrationContext.configure(conn), metadata) == []
        config.attributes["connection"] = conn
        command.downgrade(config, "base")
        assert inspect(conn).get_table_names() == ["alembic_version"]
        command.upgrade(config, "head")
        assert compare_metadata(MigrationContext.configure(conn), metadata) == []
