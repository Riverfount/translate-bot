"""
Testes para app/activitypub/handlers.py

Cobre:
- on_follow: actor remoto como string → busca e aceita
- on_follow: actor remoto já como objeto APKitActor → aceita diretamente
- on_follow: actor não resolúvel → retorna 400
- on_create: enfileira ctx.activity (não ctx) e retorna 202
- on_create: translate_text não é chamado diretamente
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apkit.models import Create, Follow, Note
from fastapi import Response
from fastapi.responses import JSONResponse


def _make_follow_ctx(actor_value, bot_actor_url="https://bot.test/users/testbot"):
    activity = Follow(
        id="https://mastodon.social/users/fulano#follows/1",
        actor=actor_value,
        object=bot_actor_url,
    )
    ctx = MagicMock()
    ctx.activity = activity
    ctx.send = AsyncMock()
    return ctx


def _make_create_ctx():
    note = Note(
        id="https://mastodon.social/statuses/1",
        attributed_to="https://mastodon.social/users/fulano",
        content="<p>Olá</p>",
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )
    activity = Create(
        id="https://mastodon.social/statuses/1/activity",
        actor="https://mastodon.social/users/fulano",
        object=note,
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )
    ctx = MagicMock()
    ctx.activity = activity
    ctx.send = AsyncMock()
    return ctx


def _get_handlers():
    """Registra os handlers num app fake e retorna o dicionário {tipo: fn}."""
    handlers = {}

    class FakeApp:
        def on(self, activity_type):
            def decorator(fn):
                handlers[activity_type.__name__] = fn
                return fn

            return decorator

    from app.activitypub import handlers as handlers_module

    handlers_module.register_handlers(FakeApp())
    return handlers


@pytest.mark.asyncio
async def test_on_follow_with_actor_as_string_accepts_and_replies():
    from apkit.models import Actor as APKitActor

    mock_follower = MagicMock(spec=APKitActor)
    mock_follower.id = "https://mastodon.social/users/fulano"
    ctx = _make_follow_ctx("https://mastodon.social/users/fulano")

    with patch("app.activitypub.handlers.ActivityPubClient") as mock_ap_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_instance.actor.fetch = AsyncMock(return_value=mock_follower)
        mock_ap_client.return_value = mock_client_instance

        handlers = _get_handlers()
        response = await handlers["Follow"](ctx)

    ctx.send.assert_called_once()
    assert isinstance(response, Response)
    assert response.status_code == 202


@pytest.mark.asyncio
async def test_on_follow_with_actor_as_object_skips_fetch():
    from apkit.models import Actor as APKitActor

    mock_follower = MagicMock(spec=APKitActor)
    mock_follower.id = "https://mastodon.social/users/fulano"
    ctx = _make_follow_ctx(mock_follower)

    with patch("app.activitypub.handlers.ActivityPubClient") as mock_ap_client:
        handlers = _get_handlers()
        response = await handlers["Follow"](ctx)

    mock_ap_client.assert_not_called()
    ctx.send.assert_called_once()
    assert response.status_code == 202


@pytest.mark.asyncio
async def test_on_follow_returns_400_when_actor_not_resolved():
    ctx = _make_follow_ctx("https://mastodon.social/users/fantasma")

    with patch("app.activitypub.handlers.ActivityPubClient") as mock_ap_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_instance.actor.fetch = AsyncMock(return_value=None)
        mock_ap_client.return_value = mock_client_instance

        handlers = _get_handlers()
        response = await handlers["Follow"](ctx)

    ctx.send.assert_not_called()
    assert isinstance(response, JSONResponse)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_on_create_enqueues_activity_not_ctx_and_returns_202():
    """Verifica que ctx.activity é enfileirado, não o ctx inteiro."""
    test_queue: asyncio.Queue = asyncio.Queue()
    ctx = _make_create_ctx()

    from app.services import queue as queue_module

    with patch.object(queue_module, "activity_queue", test_queue):
        handlers = _get_handlers()
        response = await handlers["Create"](ctx)

    assert response.status_code == 202
    assert not test_queue.empty()
    queued_item = await test_queue.get()
    # deve ser o activity, não o ctx
    assert queued_item is ctx.activity
    assert isinstance(queued_item, Create)


@pytest.mark.asyncio
async def test_on_create_does_not_call_translate():
    test_queue: asyncio.Queue = asyncio.Queue()
    ctx = _make_create_ctx()

    from app.services import queue as queue_module

    with (
        patch.object(queue_module, "activity_queue", test_queue),
        patch("app.services.translate.translate_text") as mock_translate,
    ):
        handlers = _get_handlers()
        await handlers["Create"](ctx)

    mock_translate.assert_not_called()
