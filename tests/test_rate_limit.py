"""
Testes para app/services/rate_limit.py

Cobre:
- is_rate_limited retorna False para um autor nunca visto
- is_rate_limited retorna True logo após record_request
- is_rate_limited retorna False quando o cooldown já expirou
- record_request atualiza (não duplica) o registro de um autor existente
- cooldown é configurável via settings.mention_cooldown_seconds
"""

from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
async def test_is_rate_limited_returns_false_for_unseen_actor(in_memory_db):
    from app.services.rate_limit import is_rate_limited

    result = await is_rate_limited("https://mastodon.social/users/fulano")
    assert result is False


@pytest.mark.asyncio
async def test_is_rate_limited_returns_true_immediately_after_record_request(in_memory_db):
    from app.services.rate_limit import is_rate_limited, record_request

    actor_url = "https://mastodon.social/users/fulano"
    await record_request(actor_url)

    result = await is_rate_limited(actor_url)
    assert result is True


@pytest.mark.asyncio
async def test_is_rate_limited_returns_false_after_cooldown_expires(in_memory_db):
    from app.models.mention_rate_limit import MentionRateLimit
    from app.services.rate_limit import is_rate_limited

    actor_url = "https://mastodon.social/users/fulano"
    long_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    async with in_memory_db() as session:
        async with session.begin():
            session.add(MentionRateLimit(actor_url=actor_url, last_request_at=long_ago))

    result = await is_rate_limited(actor_url)
    assert result is False


@pytest.mark.asyncio
async def test_record_request_updates_existing_actor(in_memory_db):
    from sqlalchemy import select

    from app.models.mention_rate_limit import MentionRateLimit
    from app.services.rate_limit import record_request

    actor_url = "https://mastodon.social/users/fulano"
    await record_request(actor_url)
    await record_request(actor_url)

    async with in_memory_db() as session:
        result = await session.execute(select(MentionRateLimit))
        rows = result.scalars().all()

    assert len(rows) == 1


@pytest.mark.asyncio
async def test_is_rate_limited_respects_custom_cooldown_setting(in_memory_db, monkeypatch):
    from app.config import settings
    from app.models.mention_rate_limit import MentionRateLimit
    from app.services.rate_limit import is_rate_limited

    monkeypatch.setattr(settings, "mention_cooldown_seconds", 1, raising=False)

    actor_url = "https://mastodon.social/users/fulano"
    ten_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=10)

    async with in_memory_db() as session:
        async with session.begin():
            session.add(MentionRateLimit(actor_url=actor_url, last_request_at=ten_seconds_ago))

    # cooldown de 1s, último request há 10s → já expirou
    result = await is_rate_limited(actor_url)
    assert result is False
