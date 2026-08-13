"""
app/models/mention_rate_limit.py

Modelo ORM para o cooldown de respostas por autor.

Evita que uma única conta consiga disparar respostas públicas repetidas
do bot (spam no timeline) e consumo sem limite da API de tradução —
ver app/services/rate_limit.py.
"""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MentionRateLimit(Base):
    __tablename__ = "mention_rate_limits"

    # URL canônica do actor remoto que mencionou o bot
    actor_url: Mapped[str] = mapped_column(String(2048), primary_key=True)

    # Momento da última resposta enviada para esse autor — atualizado
    # explicitamente a cada record_request (sem insert_default: o valor
    # é sempre fornecido pelo chamador)
    last_request_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<MentionRateLimit actor_url={self.actor_url!r}>"
