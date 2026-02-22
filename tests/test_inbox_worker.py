"""
Testes para workers/inbox_worker.py

Cobre:
- Post com menção ao bot → traduz e responde
- Post sem menção ao bot → ignorado silenciosamente
- Post com conteúdo vazio após remover a menção → não chama translate
- Activity com objeto que não é Note → ignorado
- Idiomas de origem e destino aparecem corretamente na resposta
- ctx.send() é chamado com o Create de resposta correto
- Erros na tradução são propagados (não engolidos silenciosamente)
- run_worker: consome item da fila e continua após erro
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from apkit.models import Note, Create


def _build_ctx(note: Note, actor_url: str = "https://mastodon.social/users/fulano"):
    activity = Create(
        id="https://mastodon.social/statuses/1/activity",
        actor=actor_url,
        object=note,
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )
    ctx = MagicMock()
    ctx.activity = activity
    ctx.send = AsyncMock()
    return ctx


def _note_with_mention(extra_text: str = "Bonjour tout le monde") -> Note:
    return Note(
        id="https://mastodon.social/statuses/1",
        attributedTo="https://mastodon.social/users/fulano",
        content=(
            f'<p><span class="mention">@testbot@bot.test</span> {extra_text}</p>'
        ),
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )


def _note_without_mention() -> Note:
    return Note(
        id="https://mastodon.social/statuses/2",
        attributedTo="https://mastodon.social/users/fulano",
        content="<p>Post sem mencionar o bot</p>",
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )


@pytest.mark.asyncio
async def test_handle_create_translates_and_replies():
    ctx = _build_ctx(_note_with_mention("Bonjour tout le monde"))
    mock_remote_actor = MagicMock()
    mock_remote_actor.id = "https://mastodon.social/users/fulano"

    with (
        patch(
            "workers.inbox_worker.translate_text",
            AsyncMock(return_value={"translated": "Olá a todos", "detected_source": "fr"}),
        ),
        patch("workers.inbox_worker.ActivityPubClient") as mock_ap_client,
    ):
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_instance.actor.fetch = AsyncMock(return_value=mock_remote_actor)
        mock_ap_client.return_value = mock_client_instance

        from workers.inbox_worker import handle_create
        await handle_create(ctx)

    ctx.send.assert_called_once()
    sent_activity = ctx.send.call_args[0][2]
    assert isinstance(sent_activity, Create)
    assert "Olá a todos" in sent_activity.object.content
    assert "FR" in sent_activity.object.content
    assert "PT" in sent_activity.object.content


@pytest.mark.asyncio
async def test_handle_create_reply_is_in_reply_to_original():
    original_id = "https://mastodon.social/statuses/42"
    note = Note(
        id=original_id,
        attributedTo="https://mastodon.social/users/fulano",
        content='<p><span class="mention">@testbot@bot.test</span> Hello</p>',
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )
    ctx = _build_ctx(note)
    mock_remote_actor = MagicMock()
    mock_remote_actor.id = "https://mastodon.social/users/fulano"

    with (
        patch(
            "workers.inbox_worker.translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "en"}),
        ),
        patch("workers.inbox_worker.ActivityPubClient") as mock_ap_client,
    ):
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_instance.actor.fetch = AsyncMock(return_value=mock_remote_actor)
        mock_ap_client.return_value = mock_client_instance

        from workers.inbox_worker import handle_create
        await handle_create(ctx)

    sent_note = ctx.send.call_args[0][2].object
    assert sent_note.in_reply_to.id == original_id


@pytest.mark.asyncio
async def test_handle_create_reply_addressed_to_author():
    ctx = _build_ctx(_note_with_mention("Hello"))
    mock_remote_actor = MagicMock()
    mock_remote_actor.id = "https://mastodon.social/users/fulano"

    with (
        patch(
            "workers.inbox_worker.translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "en"}),
        ),
        patch("workers.inbox_worker.ActivityPubClient") as mock_ap_client,
    ):
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_instance.actor.fetch = AsyncMock(return_value=mock_remote_actor)
        mock_ap_client.return_value = mock_client_instance

        from workers.inbox_worker import handle_create
        await handle_create(ctx)

    sent_note = ctx.send.call_args[0][2].object
    assert "https://mastodon.social/users/fulano" in sent_note.to


@pytest.mark.asyncio
async def test_handle_create_ignores_post_without_mention():
    ctx = _build_ctx(_note_without_mention())

    with patch("workers.inbox_worker.translate_text") as mock_translate:
        from workers.inbox_worker import handle_create
        await handle_create(ctx)

    mock_translate.assert_not_called()
    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_handle_create_ignores_empty_text_after_stripping_mention():
    note = Note(
        id="https://mastodon.social/statuses/3",
        attributedTo="https://mastodon.social/users/fulano",
        content='<p><span class="mention">@testbot@bot.test</span></p>',
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )
    ctx = _build_ctx(note)

    with patch("workers.inbox_worker.translate_text") as mock_translate:
        from workers.inbox_worker import handle_create
        await handle_create(ctx)

    mock_translate.assert_not_called()
    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_handle_create_ignores_non_note_object():
    from apkit.models import Create

    non_note = MagicMock()
    non_note.__class__ = object

    activity = MagicMock(spec=Create)
    activity.actor = "https://mastodon.social/users/fulano"
    activity.object = non_note

    ctx = MagicMock()
    ctx.activity = activity
    ctx.send = AsyncMock()

    with patch("workers.inbox_worker.translate_text") as mock_translate:
        from workers.inbox_worker import handle_create
        await handle_create(ctx)

    mock_translate.assert_not_called()
    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_handle_create_propagates_translate_error():
    import httpx

    ctx = _build_ctx(_note_with_mention("Bonjour"))

    with patch(
        "workers.inbox_worker.translate_text",
        AsyncMock(side_effect=httpx.HTTPStatusError(
            "403", request=MagicMock(), response=MagicMock()
        )),
    ):
        from workers.inbox_worker import handle_create
        with pytest.raises(httpx.HTTPStatusError):
            await handle_create(ctx)

    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_run_worker_processes_item_from_queue():
    import asyncio
    from app.services import queue as queue_module

    ctx = _build_ctx(_note_without_mention())
    test_queue: asyncio.Queue = asyncio.Queue()
    await test_queue.put(ctx)

    with (
        patch.object(queue_module, "activity_queue", test_queue),
        patch("workers.inbox_worker.handle_create", AsyncMock()) as mock_handle,
    ):
        from workers import inbox_worker
        inbox_worker.activity_queue = test_queue

        task = asyncio.create_task(inbox_worker.run_worker())
        await test_queue.join()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    mock_handle.assert_called_once_with(ctx)


@pytest.mark.asyncio
async def test_run_worker_continues_after_error():
    import asyncio

    ctx1 = _build_ctx(_note_without_mention())
    ctx2 = _build_ctx(_note_without_mention())

    test_queue: asyncio.Queue = asyncio.Queue()
    await test_queue.put(ctx1)
    await test_queue.put(ctx2)

    call_count = 0

    async def handle_side_effect(ctx):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Erro simulado no primeiro item")

    with patch("workers.inbox_worker.handle_create", side_effect=handle_side_effect):
        from workers import inbox_worker
        inbox_worker.activity_queue = test_queue

        task = asyncio.create_task(inbox_worker.run_worker())
        await asyncio.sleep(0.2)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert call_count == 2
