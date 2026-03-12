from typing import Dict

from apkit.models import Note

_notes: Dict[str, Note] = {}


def store_note(note_id: str, note: Note) -> None:
    _notes[note_id] = note


def get_note(note_id: str) -> Note | None:
    return _notes.get(note_id)
