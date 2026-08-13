"""
Testes para app/models/note.py

Cobre:
- StoredNote pode ser criada e persistida com campos obrigatórios
- note_id é a chave primária
- content é persistido como JSON
- created_at é preenchido automaticamente no INSERT
- __repr__ retorna string legível
- note_id duplicado levanta erro de integridade
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


def test_stored_note_tablename():
    from app.models.note import StoredNote

    assert StoredNote.__tablename__ == "notes"


def test_stored_note_primary_key_is_note_id():
    from app.models.note import StoredNote
    from sqlalchemy import inspect

    mapper = inspect(StoredNote)
    pk_cols = [col.key for col in mapper.primary_key]
    assert pk_cols == ["note_id"]


def test_stored_note_has_content_column():
    from app.models.note import StoredNote
    from sqlalchemy import inspect

    mapper = inspect(StoredNote)
    assert "content" in [col.key for col in mapper.columns]


def test_stored_note_has_created_at_column():
    from app.models.note import StoredNote
    from sqlalchemy import inspect

    mapper = inspect(StoredNote)
    assert "created_at" in [col.key for col in mapper.columns]


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stored_note_can_be_saved(session):
    from app.models.note import StoredNote

    note = StoredNote(
        note_id="https://bot.test/users/testbot/notes/abc",
        content={"type": "Note", "content": "<p>Olá</p>"},
    )
    session.add(note)
    await session.commit()

    result = await session.get(StoredNote, "https://bot.test/users/testbot/notes/abc")
    assert result is not None


@pytest.mark.asyncio
async def test_stored_note_content_persisted_as_json(session):
    from app.models.note import StoredNote

    note = StoredNote(
        note_id="https://bot.test/users/testbot/notes/abc",
        content={"type": "Note", "content": "<p>Olá</p>", "to": ["a", "b"]},
    )
    session.add(note)
    await session.commit()

    result = await session.get(StoredNote, "https://bot.test/users/testbot/notes/abc")
    assert result.content == {"type": "Note", "content": "<p>Olá</p>", "to": ["a", "b"]}


# ---------------------------------------------------------------------------
# created_at
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stored_note_created_at_set_automatically(session):
    from app.models.note import StoredNote

    note = StoredNote(
        note_id="https://bot.test/users/testbot/notes/abc",
        content={"type": "Note"},
    )
    session.add(note)
    await session.commit()
    await session.refresh(note)

    assert note.created_at is not None
    assert isinstance(note.created_at, datetime)


@pytest.mark.asyncio
async def test_stored_note_created_at_is_recent(session):
    from app.models.note import StoredNote

    note = StoredNote(
        note_id="https://bot.test/users/testbot/notes/abc",
        content={"type": "Note"},
    )
    session.add(note)
    await session.commit()
    await session.refresh(note)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    diff = abs((now - note.created_at.replace(tzinfo=None)).total_seconds())
    assert diff < 5


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------


def test_stored_note_repr():
    from app.models.note import StoredNote

    note = StoredNote(
        note_id="https://bot.test/users/testbot/notes/abc",
        content={"type": "Note"},
    )
    assert "https://bot.test/users/testbot/notes/abc" in repr(note)
    assert "StoredNote" in repr(note)


# ---------------------------------------------------------------------------
# Integridade e merge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stored_note_duplicate_note_id_raises(session_factory):
    """INSERT duplicado deve levantar IntegrityError."""
    from app.models.note import StoredNote

    async with session_factory() as s1:
        s1.add(
            StoredNote(
                note_id="https://bot.test/users/testbot/notes/abc",
                content={"type": "Note"},
            )
        )
        await s1.commit()

    async with session_factory() as s2:
        s2.add(
            StoredNote(
                note_id="https://bot.test/users/testbot/notes/abc",
                content={"type": "Note"},
            )
        )
        with pytest.raises(IntegrityError):
            await s2.commit()


@pytest.mark.asyncio
async def test_stored_note_merge_avoids_duplicate(session_factory):
    """session.merge deve atualizar sem erro em caso de note_id duplicado."""
    from app.models.note import StoredNote

    async with session_factory() as s1:
        await s1.merge(
            StoredNote(
                note_id="https://bot.test/users/testbot/notes/abc",
                content={"type": "Note", "content": "original"},
            )
        )
        await s1.commit()

    async with session_factory() as s2:
        await s2.merge(
            StoredNote(
                note_id="https://bot.test/users/testbot/notes/abc",
                content={"type": "Note", "content": "atualizado"},
            )
        )
        await s2.commit()

    async with session_factory() as s3:
        result = await s3.get(StoredNote, "https://bot.test/users/testbot/notes/abc")
        assert result.content["content"] == "atualizado"
