from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlunparse

from app.config import settings

def clean_database_url(url: str) -> str:
    """Remove unsupported SSL parameters for asyncpg"""
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

# Clean database URL for asyncpg compatibility
clean_url = clean_database_url(settings.DATABASE_URL)

# Async engine for FastAPI
async_engine = create_async_engine(
    clean_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
)

# Sync engine for migrations and compatibility
sync_engine = create_engine(
    clean_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
)

# Async session maker
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync session maker
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

