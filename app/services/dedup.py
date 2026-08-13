"""
app/services/dedup.py

Deduplicação de atividades processadas. Mastodon (e outras implementações
ActivityPub) reentregam atividades com retry/backoff quando a entrega
original falha — sem isso, uma reentrega do mesmo Create depois de uma
resposta já enviada com sucesso geraria uma segunda resposta pública
duplicada para o mesmo autor.
"""

from app import database as _db
from app.models.processed_activity import ProcessedActivity


async def already_processed(activity_id: str) -> bool:
    """Retorna True se essa atividade já foi processada com sucesso antes."""
    async with _db.async_session_factory() as session:
        result = await session.get(ProcessedActivity, activity_id)
    return result is not None


async def mark_processed(activity_id: str) -> None:
    """Registra a atividade como processada."""
    async with _db.async_session_factory() as session:
        async with session.begin():
            await session.merge(ProcessedActivity(activity_id=activity_id))
