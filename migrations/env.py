import os

from alembic import context
from sqlalchemy import create_engine

from ai_tutor.models import metadata


def run():
    connection = context.config.attributes.get("connection")
    if connection is not None:
        configure(connection)
    else:
        engine = create_engine(os.environ["DATABASE_URL"], hide_parameters=True)
        with engine.connect() as connection:
            configure(connection)
        engine.dispose()


def configure(connection):
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()


run()
