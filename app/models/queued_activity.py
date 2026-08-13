"""
app/models/queued_activity.py

Modelo ORM para persistência das atividades Create recebidas no inbox,
enquanto aguardam processamento pelo worker assíncrono.

Cada atividade fica na tabela até ser processada com sucesso — se o
processo cair ou reiniciar com itens pendentes, load_pending() os
recarrega na fila em memória no próximo startup (ver app/services/queue.py).
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QueuedActivity(Base):
    __tablename__ = "queued_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Payload ActivityPub já serializado (apmodel.to_dict) da atividade Create
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        insert_default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<QueuedActivity id={self.id!r}>"
