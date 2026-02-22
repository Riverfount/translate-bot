"""
Testes para app/models/follower.py

Cobre:
- Follower pode ser criado e persistido com campos obrigatórios
- actor_url é a chave primária
- inbox_url é persistido corretamente
- followed_at é preenchido automaticamente no INSERT
- followed_at tem timezone UTC
- __repr__ retorna string legível
- actor_url duplicado levanta erro de integridade
- merge evita erro de duplicidade (comportamento usado no on_follow)
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


def test_follower_tablename():
    from app.models.follower import Follower

    assert Follower.__tablename__ == "followers"


def test_follower_primary_key_is_actor_url():
    from app.models.follower import Follower
    from sqlalchemy import inspect

    mapper = inspect(Follower)
    pk_cols = [col.key for col in mapper.primary_key]
    assert pk_cols == ["actor_url"]


def test_follower_has_inbox_url_column():
    from app.models.follower import Follower
    from sqlalchemy import inspect

    mapper = inspect(Follower)
    assert "inbox_url" in [col.key for col in mapper.columns]


def test_follower_has_followed_at_column():
    from app.models.follower import Follower
    from sqlalchemy import inspect

    mapper = inspect(Follower)
    assert "followed_at" in [col.key for col in mapper.columns]


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_follower_can_be_saved(session):
    from app.models.follower import Follower

    follower = Follower(
        actor_url="https://mastodon.social/users/fulano",
        inbox_url="https://mastodon.social/users/fulano/inbox",
    )
    session.add(follower)
    await session.commit()

    result = await session.get(Follower, "https://mastodon.social/users/fulano")
    assert result is not None


@pytest.mark.asyncio
async def test_follower_actor_url_persisted(session):
    from app.models.follower import Follower

    follower = Follower(
        actor_url="https://mastodon.social/users/fulano",
        inbox_url="https://mastodon.social/users/fulano/inbox",
    )
    session.add(follower)
    await session.commit()

    result = await session.get(Follower, "https://mastodon.social/users/fulano")
    assert result.actor_url == "https://mastodon.social/users/fulano"


@pytest.mark.asyncio
async def test_follower_inbox_url_persisted(session):
    from app.models.follower import Follower

    follower = Follower(
        actor_url="https://mastodon.social/users/fulano",
        inbox_url="https://mastodon.social/users/fulano/inbox",
    )
    session.add(follower)
    await session.commit()

    result = await session.get(Follower, "https://mastodon.social/users/fulano")
    assert result.inbox_url == "https://mastodon.social/users/fulano/inbox"


# ---------------------------------------------------------------------------
# followed_at
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_follower_followed_at_set_automatically(session):
    """followed_at deve ser preenchido automaticamente no INSERT."""
    from app.models.follower import Follower

    follower = Follower(
        actor_url="https://mastodon.social/users/fulano",
        inbox_url="https://mastodon.social/users/fulano/inbox",
    )
    session.add(follower)
    await session.commit()
    await session.refresh(follower)

    assert follower.followed_at is not None
    assert isinstance(follower.followed_at, datetime)


@pytest.mark.asyncio
async def test_follower_followed_at_is_utc(session):
    """followed_at deve ter timezone UTC."""
    from app.models.follower import Follower

    follower = Follower(
        actor_url="https://mastodon.social/users/fulano",
        inbox_url="https://mastodon.social/users/fulano/inbox",
    )
    session.add(follower)
    await session.commit()
    await session.refresh(follower)

    # SQLite retorna datetime sem tzinfo — verificamos que o valor é razoável
    # (dentro dos últimos 5 segundos)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    diff = abs((now - follower.followed_at.replace(tzinfo=None)).total_seconds())
    assert diff < 5


@pytest.mark.asyncio
async def test_follower_followed_at_not_overwritten_on_update(session):
    """followed_at não deve mudar ao atualizar inbox_url."""
    from app.models.follower import Follower

    follower = Follower(
        actor_url="https://mastodon.social/users/fulano",
        inbox_url="https://mastodon.social/users/fulano/inbox",
    )
    session.add(follower)
    await session.commit()
    await session.refresh(follower)

    original_followed_at = follower.followed_at

    follower.inbox_url = "https://mastodon.social/users/fulano/inbox2"
    await session.commit()
    await session.refresh(follower)

    assert follower.followed_at == original_followed_at


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------


def test_follower_repr():
    from app.models.follower import Follower

    follower = Follower(
        actor_url="https://mastodon.social/users/fulano",
        inbox_url="https://mastodon.social/users/fulano/inbox",
    )
    assert "https://mastodon.social/users/fulano" in repr(follower)
    assert "Follower" in repr(follower)


# ---------------------------------------------------------------------------
# Integridade e merge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_follower_duplicate_actor_url_raises(session_factory):
    """INSERT duplicado deve levantar IntegrityError."""
    from app.models.follower import Follower

    async with session_factory() as s1:
        s1.add(
            Follower(
                actor_url="https://mastodon.social/users/fulano",
                inbox_url="https://mastodon.social/users/fulano/inbox",
            )
        )
        await s1.commit()

    async with session_factory() as s2:
        s2.add(
            Follower(
                actor_url="https://mastodon.social/users/fulano",
                inbox_url="https://mastodon.social/users/fulano/inbox",
            )
        )
        with pytest.raises(IntegrityError):
            await s2.commit()


@pytest.mark.asyncio
async def test_follower_merge_avoids_duplicate(session_factory):
    """session.merge deve atualizar sem erro em caso de actor_url duplicado."""
    from app.models.follower import Follower

    async with session_factory() as s1:
        await s1.merge(
            Follower(
                actor_url="https://mastodon.social/users/fulano",
                inbox_url="https://mastodon.social/users/fulano/inbox",
            )
        )
        await s1.commit()

    async with session_factory() as s2:
        await s2.merge(
            Follower(
                actor_url="https://mastodon.social/users/fulano",
                inbox_url="https://mastodon.social/users/fulano/inbox_novo",
            )
        )
        await s2.commit()

    async with session_factory() as s3:
        result = await s3.get(Follower, "https://mastodon.social/users/fulano")
        assert result.inbox_url == "https://mastodon.social/users/fulano/inbox_novo"
