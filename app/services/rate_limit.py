"""
app/services/rate_limit.py

Cooldown por autor entre respostas do bot. Sem isso, uma única conta
pode disparar respostas públicas repetidas (spam no timeline) e
consumir sem limite a API de tradução configurada.
"""

from datetime import datetime, timedelta, timezone

from app import database as _db
from app.config import settings
from app.models.mention_rate_limit import MentionRateLimit

DEFAULT_COOLDOWN_SECONDS = 30


async def is_rate_limited(actor_url: str) -> bool:
    """Retorna True se o autor ainda está dentro do período de cooldown."""
    async with _db.async_session_factory() as session:
        row = await session.get(MentionRateLimit, actor_url)

    if row is None:
        return False

    last_request_at = row.last_request_at
    if last_request_at.tzinfo is None:
        # SQLite retorna datetime sem tzinfo — assume UTC (é o que gravamos)
        last_request_at = last_request_at.replace(tzinfo=timezone.utc)

    cooldown = settings.get("mention_cooldown_seconds", DEFAULT_COOLDOWN_SECONDS)
    return datetime.now(timezone.utc) - last_request_at < timedelta(seconds=cooldown)


async def record_request(actor_url: str) -> None:
    """Registra que o autor acabou de disparar uma resposta, reiniciando o cooldown."""
    async with _db.async_session_factory() as session:
        async with session.begin():
            await session.merge(
                MentionRateLimit(actor_url=actor_url, last_request_at=datetime.now(timezone.utc))
            )
