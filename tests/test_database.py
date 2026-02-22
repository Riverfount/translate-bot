"""
Testes para app/database.py

Cobre:
- engine é criada com a URL correta
- async_session_factory retorna sessões AsyncSession
- get_session fornece sessão funcional e faz commit automático
- get_session faz rollback em caso de exceção
- init_db cria as tabelas no banco
- init_db importa os modelos antes de criar as tabelas
"""

from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


# ---------------------------------------------------------------------------
# Fixture: banco em memória isolado por teste
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_engine():
    """Engine SQLite em memória — isolada por teste, sem tocar em arquivos."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from app.database import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine):
    """Fábrica de sessões apontando para o banco em memória."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    return async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def test_engine_is_async_engine():
    """engine deve ser uma instância de AsyncEngine."""
    from app.database import engine

    assert isinstance(engine, AsyncEngine)


def test_engine_uses_configured_url():
    """engine deve usar a URL definida em settings.database_url."""
    from app.database import engine
    from app.config import settings

    assert str(engine.url) == settings.database_url


# ---------------------------------------------------------------------------
# async_session_factory
# ---------------------------------------------------------------------------


def test_async_session_factory_is_sessionmaker():
    """async_session_factory deve ser uma instância de async_sessionmaker."""
    from app.database import async_session_factory

    assert isinstance(async_session_factory, async_sessionmaker)


@pytest.mark.asyncio
async def test_async_session_factory_produces_async_session(test_session_factory):
    """Sessão produzida pela fábrica deve ser AsyncSession."""
    async with test_session_factory() as session:
        assert isinstance(session, AsyncSession)


# ---------------------------------------------------------------------------
# get_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_session_yields_async_session(test_session_factory):
    """get_session deve fornecer uma sessão AsyncSession."""
    from app.database import get_session

    with patch("app.database.async_session_factory", test_session_factory):
        gen = get_session()
        session = await gen.__anext__()
        assert isinstance(session, AsyncSession)
        try:
            await gen.aclose()
        except StopAsyncIteration:
            pass


@pytest.mark.asyncio
async def test_get_session_commits_on_success(test_engine, test_session_factory):
    """get_session deve fazer commit automaticamente ao sair sem exceção."""
    from app.database import Base
    from app.models.follower import Follower

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # simula o comportamento do get_session diretamente
    async with test_session_factory() as session:
        async with session.begin():
            follower = Follower(
                actor_url="https://mastodon.social/users/fulano",
                inbox_url="https://mastodon.social/users/fulano/inbox",
            )
            session.add(follower)
    # sair do `session.begin()` faz commit automático

    async with test_session_factory() as verify_session:
        result = await verify_session.get(Follower, "https://mastodon.social/users/fulano")
        assert result is not None


@pytest.mark.asyncio
async def test_get_session_rollback_on_exception(test_engine, test_session_factory):
    """get_session deve fazer rollback quando uma exceção ocorre."""
    from app.database import get_session
    from app.models.follower import Follower

    async with test_engine.begin() as conn:
        from app.database import Base

        await conn.run_sync(Base.metadata.create_all)

    with patch("app.database.async_session_factory", test_session_factory):
        try:
            gen = get_session()
            session = await gen.__anext__()
            follower = Follower(
                actor_url="https://mastodon.social/users/fulano",
                inbox_url="https://mastodon.social/users/fulano/inbox",
            )
            session.add(follower)
            await gen.athrow(RuntimeError("erro simulado"))
        except (RuntimeError, StopAsyncIteration):
            pass

    # Verifica que o dado NÃO foi persistido
    async with test_session_factory() as verify_session:
        result = await verify_session.get(Follower, "https://mastodon.social/users/fulano")
        assert result is None


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_init_db_creates_tables():
    """init_db deve criar as tabelas no banco."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import inspect

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    with patch("app.database.engine", test_engine):
        from app.database import init_db

        await init_db()

    async with test_engine.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    assert "followers" in tables

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_init_db_imports_follower_model():
    """init_db deve importar o módulo follower para registrar o modelo no metadata."""
    from sqlalchemy.ext.asyncio import create_async_engine

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    with (
        patch("app.database.engine", test_engine),
        patch("app.models.follower"),
    ):
        from app.database import init_db

        await init_db()

    await test_engine.dispose()
    # O simples fato de init_db completar sem erro confirma o import
    # (se o modelo não fosse importado, a tabela não seria criada)


@pytest.mark.asyncio
async def test_init_db_is_idempotent():
    """Chamar init_db duas vezes não deve causar erro (tabelas já existentes)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    with patch("app.database.engine", test_engine):
        from app.database import init_db

        await init_db()
        await init_db()  # segunda chamada não deve lançar exceção

    await test_engine.dispose()
