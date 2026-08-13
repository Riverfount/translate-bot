"""
Testes para app/models/queued_activity.py

Cobre:
- QueuedActivity pode ser criada e persistida com campos obrigatórios
- id é a chave primária e é autoincrementado
- payload é persistido como JSON
- created_at é preenchido automaticamente no INSERT
- __repr__ retorna string legível
"""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
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


def test_queued_activity_tablename():
    from app.models.queued_activity import QueuedActivity

    assert QueuedActivity.__tablename__ == "queued_activities"


def test_queued_activity_primary_key_is_id():
    from app.models.queued_activity import QueuedActivity
    from sqlalchemy import inspect

    mapper = inspect(QueuedActivity)
    pk_cols = [col.key for col in mapper.primary_key]
    assert pk_cols == ["id"]


def test_queued_activity_has_payload_column():
    from app.models.queued_activity import QueuedActivity
    from sqlalchemy import inspect

    mapper = inspect(QueuedActivity)
    assert "payload" in [col.key for col in mapper.columns]


def test_queued_activity_has_created_at_column():
    from app.models.queued_activity import QueuedActivity
    from sqlalchemy import inspect

    mapper = inspect(QueuedActivity)
    assert "created_at" in [col.key for col in mapper.columns]


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_queued_activity_can_be_saved(session):
    from app.models.queued_activity import QueuedActivity

    row = QueuedActivity(payload={"type": "Create", "actor": "https://mastodon.social/users/x"})
    session.add(row)
    await session.commit()

    assert row.id is not None


@pytest.mark.asyncio
async def test_queued_activity_id_autoincrements(session):
    from app.models.queued_activity import QueuedActivity

    row1 = QueuedActivity(payload={"type": "Create"})
    row2 = QueuedActivity(payload={"type": "Create"})
    session.add(row1)
    session.add(row2)
    await session.commit()

    assert row1.id != row2.id


@pytest.mark.asyncio
async def test_queued_activity_payload_persisted_as_json(session):
    from app.models.queued_activity import QueuedActivity

    payload = {"type": "Create", "actor": "https://mastodon.social/users/x", "to": ["a", "b"]}
    row = QueuedActivity(payload=payload)
    session.add(row)
    await session.commit()

    result = await session.get(QueuedActivity, row.id)
    assert result.payload == payload


# ---------------------------------------------------------------------------
# created_at
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_queued_activity_created_at_set_automatically(session):
    from app.models.queued_activity import QueuedActivity

    row = QueuedActivity(payload={"type": "Create"})
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assert row.created_at is not None
    assert isinstance(row.created_at, datetime)


@pytest.mark.asyncio
async def test_queued_activity_created_at_is_recent(session):
    from app.models.queued_activity import QueuedActivity

    row = QueuedActivity(payload={"type": "Create"})
    session.add(row)
    await session.commit()
    await session.refresh(row)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    diff = abs((now - row.created_at.replace(tzinfo=None)).total_seconds())
    assert diff < 5


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_queued_activity_repr(session):
    from app.models.queued_activity import QueuedActivity

    row = QueuedActivity(payload={"type": "Create"})
    session.add(row)
    await session.commit()

    assert "QueuedActivity" in repr(row)
    assert str(row.id) in repr(row)
