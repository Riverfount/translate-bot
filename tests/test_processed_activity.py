"""
Testes para app/models/processed_activity.py

Cobre:
- ProcessedActivity pode ser criada e persistida com campos obrigatórios
- activity_id é a chave primária
- processed_at é preenchido automaticamente no INSERT
- __repr__ retorna string legível
- activity_id duplicado levanta erro de integridade
- merge evita erro de duplicidade
"""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    from app.database import Base

    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as s:
        yield s


# ---------------------------------------------------------------------------
# Estrutura do modelo
# ---------------------------------------------------------------------------


def test_processed_activity_tablename():
    from app.models.processed_activity import ProcessedActivity

    assert ProcessedActivity.__tablename__ == "processed_activities"


def test_processed_activity_primary_key_is_activity_id():
    from app.models.processed_activity import ProcessedActivity
    from sqlalchemy import inspect

    mapper = inspect(ProcessedActivity)
    pk_cols = [col.key for col in mapper.primary_key]
    assert pk_cols == ["activity_id"]


def test_processed_activity_has_processed_at_column():
    from app.models.processed_activity import ProcessedActivity
    from sqlalchemy import inspect

    mapper = inspect(ProcessedActivity)
    assert "processed_at" in [col.key for col in mapper.columns]


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_processed_activity_can_be_saved(session):
    from app.models.processed_activity import ProcessedActivity

    row = ProcessedActivity(activity_id="https://mastodon.social/statuses/1/activity")
    session.add(row)
    await session.commit()

    result = await session.get(ProcessedActivity, "https://mastodon.social/statuses/1/activity")
    assert result is not None


# ---------------------------------------------------------------------------
# processed_at
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_processed_activity_processed_at_set_automatically(session):
    from app.models.processed_activity import ProcessedActivity

    row = ProcessedActivity(activity_id="https://mastodon.social/statuses/1/activity")
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assert row.processed_at is not None
    assert isinstance(row.processed_at, datetime)


@pytest.mark.asyncio
async def test_processed_activity_processed_at_is_recent(session):
    from app.models.processed_activity import ProcessedActivity

    row = ProcessedActivity(activity_id="https://mastodon.social/statuses/1/activity")
    session.add(row)
    await session.commit()
    await session.refresh(row)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    diff = abs((now - row.processed_at.replace(tzinfo=None)).total_seconds())
    assert diff < 5


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------


def test_processed_activity_repr():
    from app.models.processed_activity import ProcessedActivity

    row = ProcessedActivity(activity_id="https://mastodon.social/statuses/1/activity")
    assert "https://mastodon.social/statuses/1/activity" in repr(row)
    assert "ProcessedActivity" in repr(row)


# ---------------------------------------------------------------------------
# Integridade e merge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_processed_activity_duplicate_activity_id_raises(session_factory):
    """INSERT duplicado deve levantar IntegrityError."""
    from app.models.processed_activity import ProcessedActivity

    async with session_factory() as s1:
        s1.add(ProcessedActivity(activity_id="https://mastodon.social/statuses/1/activity"))
        await s1.commit()

    async with session_factory() as s2:
        s2.add(ProcessedActivity(activity_id="https://mastodon.social/statuses/1/activity"))
        with pytest.raises(IntegrityError):
            await s2.commit()


@pytest.mark.asyncio
async def test_processed_activity_merge_avoids_duplicate(session_factory):
    """session.merge deve funcionar sem erro em caso de activity_id duplicado."""
    from app.models.processed_activity import ProcessedActivity

    async with session_factory() as s1:
        await s1.merge(ProcessedActivity(activity_id="https://mastodon.social/statuses/1/activity"))
        await s1.commit()

    async with session_factory() as s2:
        await s2.merge(ProcessedActivity(activity_id="https://mastodon.social/statuses/1/activity"))
        await s2.commit()

    async with session_factory() as s3:
        result = await s3.get(ProcessedActivity, "https://mastodon.social/statuses/1/activity")
        assert result is not None
