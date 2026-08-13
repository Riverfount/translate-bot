"""
Testes para app/services/queue.py

Cobre:
- enqueue persiste a atividade no banco (apmodel.to_dict)
- enqueue coloca (row_id, activity) na fila em memória
- dequeue remove a atividade persistida
- load_pending recarrega itens pendentes (deixados por um crash anterior)
  na fila em memória, reconstruindo o objeto Create via apmodel.load
- load_pending não faz nada quando não há itens pendentes
"""

import asyncio

import apmodel
import pytest
from apkit.models import Create


@pytest.fixture(autouse=True)
def fresh_activity_queue():
    """Cada teste começa com uma fila em memória vazia e isolada."""
    import app.services.queue as queue_module

    original = queue_module.activity_queue
    queue_module.activity_queue = asyncio.Queue()
    yield queue_module.activity_queue
    queue_module.activity_queue = original


@pytest.mark.asyncio
async def test_enqueue_persists_to_db(in_memory_db, make_create):
    from app.models.queued_activity import QueuedActivity
    from app.services.queue import enqueue

    activity = make_create()
    await enqueue(activity)

    async with in_memory_db() as session:
        from sqlalchemy import select

        result = await session.execute(select(QueuedActivity))
        rows = result.scalars().all()

    assert len(rows) == 1
    assert rows[0].payload == apmodel.to_dict(activity)


@pytest.mark.asyncio
async def test_enqueue_puts_item_on_memory_queue(in_memory_db, make_create, fresh_activity_queue):
    from app.services.queue import enqueue

    activity = make_create()
    await enqueue(activity)

    assert not fresh_activity_queue.empty()
    row_id, queued_activity = await fresh_activity_queue.get()
    assert isinstance(row_id, int)
    assert queued_activity is activity


@pytest.mark.asyncio
async def test_dequeue_removes_from_db(in_memory_db, make_create, fresh_activity_queue):
    from app.models.queued_activity import QueuedActivity
    from app.services.queue import dequeue, enqueue

    activity = make_create()
    await enqueue(activity)
    row_id, _ = await fresh_activity_queue.get()

    await dequeue(row_id)

    async with in_memory_db() as session:
        result = await session.get(QueuedActivity, row_id)
    assert result is None


@pytest.mark.asyncio
async def test_load_pending_reloads_items_into_memory_queue(
    in_memory_db, make_create, fresh_activity_queue
):
    from app.models.queued_activity import QueuedActivity
    from app.services.queue import load_pending

    activity = make_create()
    payload = apmodel.to_dict(activity)

    async with in_memory_db() as session:
        async with session.begin():
            row = QueuedActivity(payload=payload)
            session.add(row)
        await session.refresh(row)
        row_id = row.id

    await load_pending()

    assert not fresh_activity_queue.empty()
    loaded_row_id, loaded_activity = await fresh_activity_queue.get()
    assert loaded_row_id == row_id
    assert isinstance(loaded_activity, Create)
    assert loaded_activity.actor == activity.actor


@pytest.mark.asyncio
async def test_load_pending_with_no_pending_items_does_nothing(in_memory_db, fresh_activity_queue):
    from app.services.queue import load_pending

    await load_pending()

    assert fresh_activity_queue.empty()
