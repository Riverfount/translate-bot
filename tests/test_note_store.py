"""
Testes para app/services/note_store.py

Cobre:
- store_note persiste a nota no banco (sobrevive a reinstanciar a sessão)
- store_note grava o payload já serializado via apmodel.to_dict
- get_note retorna o payload persistido
- get_note retorna None quando a nota não existe
- store_note com o mesmo note_id atualiza o conteúdo (merge, sem erro de duplicidade)
"""

import apmodel
import pytest


@pytest.mark.asyncio
async def test_store_note_persists_to_db(in_memory_db, make_note):
    from app.models.note import StoredNote
    from app.services.note_store import store_note

    note = make_note(note_id="https://bot.test/users/testbot/notes/abc")
    await store_note("https://bot.test/users/testbot/notes/abc", note)

    async with in_memory_db() as session:
        result = await session.get(StoredNote, "https://bot.test/users/testbot/notes/abc")
        assert result is not None


@pytest.mark.asyncio
async def test_store_note_content_matches_apmodel_to_dict(in_memory_db, make_note):
    from app.models.note import StoredNote
    from app.services.note_store import store_note

    note = make_note(note_id="https://bot.test/users/testbot/notes/abc")
    await store_note("https://bot.test/users/testbot/notes/abc", note)

    async with in_memory_db() as session:
        result = await session.get(StoredNote, "https://bot.test/users/testbot/notes/abc")
        assert result.content == apmodel.to_dict(note)


@pytest.mark.asyncio
async def test_get_note_returns_stored_content(in_memory_db, make_note):
    from app.services.note_store import get_note, store_note

    note = make_note(
        note_id="https://bot.test/users/testbot/notes/abc",
        content="<p>Olá mundo</p>",
    )
    await store_note("https://bot.test/users/testbot/notes/abc", note)

    result = await get_note("https://bot.test/users/testbot/notes/abc")
    assert result is not None
    assert result["content"] == "<p>Olá mundo</p>"


@pytest.mark.asyncio
async def test_get_note_returns_none_when_missing(in_memory_db):
    from app.services.note_store import get_note

    result = await get_note("https://bot.test/users/testbot/notes/nao-existe")
    assert result is None


@pytest.mark.asyncio
async def test_store_note_overwrites_existing_note_id(in_memory_db, make_note):
    """Reenviar a mesma nota (mesmo note_id) não deve levantar erro de duplicidade."""
    from app.services.note_store import get_note, store_note

    note_id = "https://bot.test/users/testbot/notes/abc"
    await store_note(note_id, make_note(note_id=note_id, content="<p>original</p>"))
    await store_note(note_id, make_note(note_id=note_id, content="<p>atualizado</p>"))

    result = await get_note(note_id)
    assert result["content"] == "<p>atualizado</p>"
