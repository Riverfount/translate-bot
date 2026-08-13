"""
Testes para app/services/dedup.py

Cobre:
- already_processed retorna False para um activity_id nunca visto
- already_processed retorna True depois de mark_processed
- mark_processed é idempotente (chamar duas vezes para o mesmo id não quebra)
"""

import pytest


@pytest.mark.asyncio
async def test_already_processed_returns_false_for_unseen_id(in_memory_db):
    from app.services.dedup import already_processed

    result = await already_processed("https://mastodon.social/statuses/1/activity")
    assert result is False


@pytest.mark.asyncio
async def test_already_processed_returns_true_after_mark_processed(in_memory_db):
    from app.services.dedup import already_processed, mark_processed

    activity_id = "https://mastodon.social/statuses/1/activity"
    await mark_processed(activity_id)

    result = await already_processed(activity_id)
    assert result is True


@pytest.mark.asyncio
async def test_mark_processed_is_idempotent(in_memory_db):
    from app.services.dedup import mark_processed

    activity_id = "https://mastodon.social/statuses/1/activity"
    await mark_processed(activity_id)
    await mark_processed(activity_id)  # não deve levantar erro de duplicidade


@pytest.mark.asyncio
async def test_already_processed_is_specific_to_activity_id(in_memory_db):
    from app.services.dedup import already_processed, mark_processed

    await mark_processed("https://mastodon.social/statuses/1/activity")

    assert await already_processed("https://mastodon.social/statuses/1/activity") is True
    assert await already_processed("https://mastodon.social/statuses/2/activity") is False
