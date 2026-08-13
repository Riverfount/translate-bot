"""
Testes para app/models/mention_rate_limit.py

Cobre:
- MentionRateLimit pode ser criada e persistida com campos obrigatórios
- actor_url é a chave primária
- last_request_at é persistido corretamente
- __repr__ retorna string legível
- actor_url duplicado levanta erro de integridade
- merge atualiza last_request_at sem duplicar o registro
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


def test_mention_rate_limit_tablename():
    from app.models.mention_rate_limit import MentionRateLimit

    assert MentionRateLimit.__tablename__ == "mention_rate_limits"


def test_mention_rate_limit_primary_key_is_actor_url():
    from app.models.mention_rate_limit import MentionRateLimit
    from sqlalchemy import inspect

    mapper = inspect(MentionRateLimit)
    pk_cols = [col.key for col in mapper.primary_key]
    assert pk_cols == ["actor_url"]


def test_mention_rate_limit_has_last_request_at_column():
    from app.models.mention_rate_limit import MentionRateLimit
    from sqlalchemy import inspect

    mapper = inspect(MentionRateLimit)
    assert "last_request_at" in [col.key for col in mapper.columns]


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mention_rate_limit_can_be_saved(session):
    from app.models.mention_rate_limit import MentionRateLimit

    now = datetime.now(timezone.utc)
    row = MentionRateLimit(actor_url="https://mastodon.social/users/fulano", last_request_at=now)
    session.add(row)
    await session.commit()

    result = await session.get(MentionRateLimit, "https://mastodon.social/users/fulano")
    assert result is not None


@pytest.mark.asyncio
async def test_mention_rate_limit_last_request_at_persisted(session):
    from app.models.mention_rate_limit import MentionRateLimit

    now = datetime.now(timezone.utc)
    row = MentionRateLimit(actor_url="https://mastodon.social/users/fulano", last_request_at=now)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    diff = abs(
        (now.replace(tzinfo=None) - row.last_request_at.replace(tzinfo=None)).total_seconds()
    )
    assert diff < 1


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------


def test_mention_rate_limit_repr():
    from app.models.mention_rate_limit import MentionRateLimit

    row = MentionRateLimit(
        actor_url="https://mastodon.social/users/fulano",
        last_request_at=datetime.now(timezone.utc),
    )
    assert "https://mastodon.social/users/fulano" in repr(row)
    assert "MentionRateLimit" in repr(row)


# ---------------------------------------------------------------------------
# Integridade e merge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mention_rate_limit_duplicate_actor_url_raises(session_factory):
    """INSERT duplicado deve levantar IntegrityError."""
    from app.models.mention_rate_limit import MentionRateLimit

    async with session_factory() as s1:
        s1.add(
            MentionRateLimit(
                actor_url="https://mastodon.social/users/fulano",
                last_request_at=datetime.now(timezone.utc),
            )
        )
        await s1.commit()

    async with session_factory() as s2:
        s2.add(
            MentionRateLimit(
                actor_url="https://mastodon.social/users/fulano",
                last_request_at=datetime.now(timezone.utc),
            )
        )
        with pytest.raises(IntegrityError):
            await s2.commit()


@pytest.mark.asyncio
async def test_mention_rate_limit_merge_updates_without_duplicating(session_factory):
    """session.merge deve atualizar last_request_at sem erro de duplicidade."""
    from app.models.mention_rate_limit import MentionRateLimit

    original = datetime(2020, 1, 1, tzinfo=timezone.utc)
    updated = datetime(2020, 1, 1, 0, 1, tzinfo=timezone.utc)

    async with session_factory() as s1:
        await s1.merge(
            MentionRateLimit(
                actor_url="https://mastodon.social/users/fulano", last_request_at=original
            )
        )
        await s1.commit()

    async with session_factory() as s2:
        await s2.merge(
            MentionRateLimit(
                actor_url="https://mastodon.social/users/fulano", last_request_at=updated
            )
        )
        await s2.commit()

    async with session_factory() as s3:
        result = await s3.get(MentionRateLimit, "https://mastodon.social/users/fulano")
        assert result.last_request_at.replace(tzinfo=None) == updated.replace(tzinfo=None)
