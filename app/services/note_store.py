"""
app/services/note_store.py

Persiste as notas de resposta publicadas pelo bot em SQLite, para que
GET /users/{identifier}/notes/{note_id} continue resolvendo o objeto
mesmo depois de um restart do processo.
"""

from typing import Any

import apmodel
from apkit.models import Note

from app import database as _db
from app.models.note import StoredNote


async def store_note(note_id: str, note: Note) -> None:
    content = apmodel.to_dict(note)
    async with _db.async_session_factory() as session:
        async with session.begin():
            await session.merge(StoredNote(note_id=note_id, content=content))


async def get_note(note_id: str) -> dict[str, Any] | None:
    async with _db.async_session_factory() as session:
        stored = await session.get(StoredNote, note_id)
    return stored.content if stored else None
