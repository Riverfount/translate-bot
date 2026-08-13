"""
app/models/note.py

Modelo ORM para persistência das notas de resposta publicadas pelo bot.

Armazena o payload ActivityPub já serializado (via apmodel.to_dict) de cada
Note enviada como resposta, permitindo que GET /users/{identifier}/notes/{note_id}
continue resolvendo o objeto após um restart do processo.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StoredNote(Base):
    __tablename__ = "notes"

    # ID completo da nota (URL) — o mesmo usado como `id` do Note ActivityPub
    note_id: Mapped[str] = mapped_column(String(2048), primary_key=True)

    # Payload ActivityPub já serializado (apmodel.to_dict), pronto para responder
    content: Mapped[dict[str, Any]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        insert_default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<StoredNote note_id={self.note_id!r}>"
