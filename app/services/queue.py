"""
app/services/queue.py

Fila de atividades compartilhada entre os handlers HTTP e o worker
assíncrono. Cada atividade enfileirada também é persistida em SQLite
(QueuedActivity) até ser processada com sucesso, para que nenhuma
menção seja perdida se o processo cair ou reiniciar com itens pendentes.

A fila em memória (activity_queue) continua sendo o caminho rápido de
sinalização entre handler e worker — a persistência serve como log de
recuperação, lida uma vez no startup via load_pending().
"""

import asyncio

import apmodel
from apkit.models import Create
from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from app import database as _db
from app.models.queued_activity import QueuedActivity

activity_queue: asyncio.Queue[tuple[int, Create]] = asyncio.Queue()


async def enqueue(activity: Create) -> None:
    """Persiste a atividade e a coloca na fila em memória para processamento."""
    payload = apmodel.to_dict(activity)
    row = QueuedActivity(payload=payload)
    async with _db.async_session_factory() as session:
        async with session.begin():
            session.add(row)
            await session.flush()
            row_id = row.id
    await activity_queue.put((row_id, activity))


async def dequeue(activity_id: int) -> None:
    """Remove a atividade persistida após processamento bem-sucedido."""
    async with _db.async_session_factory() as session:
        async with session.begin():
            await session.execute(sa_delete(QueuedActivity).where(QueuedActivity.id == activity_id))


async def load_pending() -> None:
    """
    Recarrega na fila em memória atividades persistidas de uma execução
    anterior (processo reiniciado com itens ainda não processados).
    Chamado uma vez no startup do worker.
    """
    async with _db.async_session_factory() as session:
        result = await session.execute(select(QueuedActivity).order_by(QueuedActivity.id))
        rows = result.scalars().all()

    for row in rows:
        activity = apmodel.load(row.payload)
        await activity_queue.put((row.id, activity))
