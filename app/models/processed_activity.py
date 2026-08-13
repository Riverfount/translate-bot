"""
app/models/processed_activity.py

Modelo ORM para deduplicação de atividades Create já processadas.

Mastodon (e outras implementações ActivityPub) reentregam atividades
com retry/backoff quando a entrega original falha. Sem registrar o
activity_id já processado, uma reentrega do mesmo Create depois de uma
resposta já enviada com sucesso geraria uma segunda resposta pública
duplicada para o mesmo autor (ver handle_create em workers/inbox_worker.py).
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProcessedActivity(Base):
    __tablename__ = "processed_activities"

    # ID da atividade ActivityPub (ex: "https://mastodon.social/statuses/1/activity")
    activity_id: Mapped[str] = mapped_column(String(2048), primary_key=True)

    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        insert_default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<ProcessedActivity activity_id={self.activity_id!r}>"
