from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.db.base import Base
from app.models import *  # Import all models

# Ensure all models are imported
from app.models.candidate import Candidate
from app.models.employer import Employer
from app.models.vacancy import Vacancy
from app.models.response import CandidateResponse
from app.models.chat import ChatMessage

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Prefer async URL if provided; fallback to sync
db_url = settings.DATABASE_URL or ""
if "+asyncpg" in db_url:
    config.set_main_option("sqlalchemy.url", db_url)
else:
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    clean_url = clean_database_url(url)
    
    context.configure(
        url=clean_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online_sync() -> None:
    """Run migrations using sync engine."""
    url = config.get_main_option("sqlalchemy.url")
    clean_url = clean_database_url(url)
    
    # Update config with cleaned URL
    config.set_main_option("sqlalchemy.url", clean_url)
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def clean_database_url(url: str) -> str:
    """Remove unsupported SSL parameters for asyncpg"""
    from urllib.parse import urlparse, parse_qs, urlunparse
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Remove all unsupported parameters for asyncpg
    unsupported_params = [
        'sslmode', 'sslcert', 'sslkey', 'sslrootcert',
        'channel_binding', 'gssencmode', 'target_session_attrs',
        'application_name', 'fallback_application_name'
    ]
    for param in unsupported_params:
        query_params.pop(param, None)
    
    # Rebuild query string
    new_query = '&'.join([f"{k}={v[0]}" for k, v in query_params.items()])
    new_parsed = parsed._replace(query=new_query)
    
    return urlunparse(new_parsed)

async def run_migrations_online_async() -> None:
    """Run migrations using async engine if URL is async."""
    url = config.get_main_option("sqlalchemy.url")
    clean_url = clean_database_url(url)
    connectable = create_async_engine(clean_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Choose async or sync runner by URL
    if "+asyncpg" in config.get_main_option("sqlalchemy.url"):
        asyncio.run(run_migrations_online_async())
    else:
        run_migrations_online_sync()

