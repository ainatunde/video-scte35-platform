import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make app importable from alembic context
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base  # noqa: E402
import app.models  # noqa: E402, F401 - ensure models are registered

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from DATABASE_URL environment variable when present.
# Converts asyncpg URL to a synchronous psycopg2 URL for Alembic's sync engine.
_env_db_url = os.environ.get("DATABASE_URL")
if _env_db_url:
    _sync_url = (
        _env_db_url
        .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        .replace("postgres://", "postgresql+psycopg2://")
    )
    config.set_main_option("sqlalchemy.url", _sync_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
