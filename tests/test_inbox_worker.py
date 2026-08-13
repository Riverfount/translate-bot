"""
Testes para workers/inbox_worker.py

Cobre:
- Post com menção ao bot → traduz e responde via ActivityPubClient.post
- Post sem menção ao bot → ignorado silenciosamente
- Post com conteúdo vazio após remover a menção → não chama translate
- Activity com objeto que não é Note → ignorado
- Idiomas de origem e destino aparecem corretamente na resposta
- Create de resposta tem in_reply_to, tag de menção e campos obrigatórios
- sign_with=["draft-cavage"] é usado no envio
- Erros no envio são logados mas não propagados
- run_worker: consome activity da fila (não ctx) e continua após erro
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apkit.models import Create, Note
from apkit.types import ActorKey
from cryptography.hazmat.primitives.asymmetric import rsa


# ---------------------------------------------------------------------------
# store_note é persistido em banco (issue #11) — mockado aqui porque estes
# são testes unitários do worker, não da persistência (ver test_note_store.py).
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_store_note():
    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "store_note", AsyncMock()) as mock:
        yield mock


# ---------------------------------------------------------------------------
# A fila é persistida em banco (issue #12) — load_pending/dequeue mockados
# aqui porque estes são testes unitários do worker, não da persistência
# da fila (ver test_queue.py).
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_load_pending():
    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "load_pending", AsyncMock()) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_dequeue():
    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "dequeue", AsyncMock()) as mock:
        yield mock


# ---------------------------------------------------------------------------
# Deduplicação de atividades (issue #13) — mockadas aqui porque estes são
# testes unitários do worker, não da persistência (ver test_dedup.py).
# already_processed default False: por padrão, os testes exercitam o
# caminho normal (atividade nova, ainda não vista).
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_already_processed():
    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "already_processed", AsyncMock(return_value=False)) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_mark_processed():
    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "mark_processed", AsyncMock()) as mock:
        yield mock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _make_actor_key():
    return ActorKey(
        key_id="https://bot.test/users/testbot#main-key",
        private_key=_make_rsa_key(),
    )


def _build_activity(note: Note, actor_url: str = "https://mastodon.social/users/fulano") -> Create:
    """Retorna um Create diretamente — handle_create recebe activity, não ctx."""
    return Create(
        id="https://mastodon.social/statuses/1/activity",
        actor=actor_url,
        object=note,
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )


def _note_with_mention(extra_text: str = "Bonjour tout le monde") -> Note:
    return Note(
        id="https://mastodon.social/statuses/1",
        attributed_to="https://mastodon.social/users/fulano",
        content=(
            '<p><span class="mention">'
            '<a href="https://bot.test/users/testbot">@testbot</a>'
            f"</span> {extra_text}</p>"
        ),
        tag=[{"type": "Mention", "href": "https://bot.test/users/testbot", "name": "@testbot"}],
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )


def _note_without_mention() -> Note:
    return Note(
        id="https://mastodon.social/statuses/2",
        attributed_to="https://mastodon.social/users/fulano",
        content="<p>Post sem mencionar o bot</p>",
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )


def _make_remote_actor(url: str = "https://mastodon.social/users/fulano"):
    actor = MagicMock()
    actor.id = url
    actor.preferred_username = url.rstrip("/").split("/")[-1]
    actor.inbox = f"{url}/inbox"
    actor.endpoints = None
    return actor


def _mock_ap_client(remote_actor):
    """
    Retorna dois mocks de ActivityPubClient — um para o actor.fetch
    e outro para o post — já que handle_create usa dois `async with` separados.
    """
    # mock da resposta HTTP do post
    mock_response = AsyncMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    mock_response.status = 202
    mock_response.text = AsyncMock(return_value="")

    # instância retornada pelo primeiro async with — para actor.fetch
    mock_fetch_instance = MagicMock()
    mock_fetch_instance.actor = MagicMock()
    mock_fetch_instance.actor.fetch = AsyncMock(return_value=remote_actor)
    mock_fetch_client = AsyncMock()
    mock_fetch_client.__aenter__ = AsyncMock(return_value=mock_fetch_instance)
    mock_fetch_client.__aexit__ = AsyncMock(return_value=False)

    # instância retornada pelo segundo async with — para post
    mock_post_instance = MagicMock()
    mock_post_instance.post = MagicMock(return_value=mock_response)
    mock_post_client = AsyncMock()
    mock_post_client.__aenter__ = AsyncMock(return_value=mock_post_instance)
    mock_post_client.__aexit__ = AsyncMock(return_value=False)

    return mock_fetch_client, mock_post_client


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_create_translates_and_calls_client_post():
    """Tradução ocorre e ActivityPubClient.post é chamado com Create assinado."""
    activity = _build_activity(_note_with_mention("Bonjour tout le monde"))
    remote_actor = _make_remote_actor()
    mock_fetch_client, mock_post_client = _mock_ap_client(remote_actor)

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá a todos", "detected_source": "fr"}),
        ),
        patch.object(
            worker_module, "ActivityPubClient", side_effect=[mock_fetch_client, mock_post_client]
        ),
        patch.object(worker_module, "get_bot_keys", AsyncMock(return_value=[_make_actor_key()])),
    ):
        await worker_module.handle_create(activity)

    mock_post_instance = mock_post_client.__aenter__.return_value
    mock_post_instance.post.assert_called_once()
    sent_activity = mock_post_instance.post.call_args.kwargs["json"]
    assert isinstance(sent_activity, Create)
    assert "Olá a todos" in sent_activity.object.content
    assert "FR" in sent_activity.object.content
    assert "PT" in sent_activity.object.content


@pytest.mark.asyncio
async def test_handle_create_awaits_store_note_with_reply_note(mock_store_note):
    """store_note (persistência em banco, issue #11) é chamado com o note_id e a Note de resposta."""
    activity = _build_activity(_note_with_mention("Bonjour"))
    remote_actor = _make_remote_actor()
    mock_fetch_client, mock_post_client = _mock_ap_client(remote_actor)

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "fr"}),
        ),
        patch.object(
            worker_module, "ActivityPubClient", side_effect=[mock_fetch_client, mock_post_client]
        ),
        patch.object(worker_module, "get_bot_keys", AsyncMock(return_value=[_make_actor_key()])),
    ):
        await worker_module.handle_create(activity)

    mock_store_note.assert_awaited_once()
    stored_note_id, stored_note = mock_store_note.call_args.args
    assert stored_note_id == stored_note.id
    assert isinstance(stored_note, Note)


@pytest.mark.asyncio
async def test_handle_create_reply_has_correct_in_reply_to():
    """Note de resposta tem in_reply_to apontando para o post original."""
    original_id = "https://mastodon.social/statuses/42"
    note = Note(
        id=original_id,
        attributed_to="https://mastodon.social/users/fulano",
        content='<p><span class="mention"><a href="https://bot.test/users/testbot">@testbot</a></span> Hello</p>',
        tag=[{"type": "Mention", "href": "https://bot.test/users/testbot", "name": "@testbot"}],
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )
    activity = _build_activity(note)
    remote_actor = _make_remote_actor()
    mock_fetch_client, mock_post_client = _mock_ap_client(remote_actor)

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "en"}),
        ),
        patch.object(
            worker_module, "ActivityPubClient", side_effect=[mock_fetch_client, mock_post_client]
        ),
        patch.object(worker_module, "get_bot_keys", AsyncMock(return_value=[_make_actor_key()])),
    ):
        await worker_module.handle_create(activity)

    mock_post_instance = mock_post_client.__aenter__.return_value
    sent_note = mock_post_instance.post.call_args.kwargs["json"].object
    assert sent_note.in_reply_to.id == original_id


@pytest.mark.asyncio
async def test_handle_create_reply_is_public():
    """Note de resposta é pública: #Public em 'to' e autor em 'cc'."""
    author_url = "https://mastodon.social/users/fulano"
    activity = _build_activity(_note_with_mention("Hello"), actor_url=author_url)
    remote_actor = _make_remote_actor(author_url)
    mock_fetch_client, mock_post_client = _mock_ap_client(remote_actor)

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "en"}),
        ),
        patch.object(
            worker_module, "ActivityPubClient", side_effect=[mock_fetch_client, mock_post_client]
        ),
        patch.object(worker_module, "get_bot_keys", AsyncMock(return_value=[_make_actor_key()])),
    ):
        await worker_module.handle_create(activity)

    mock_post_instance = mock_post_client.__aenter__.return_value
    sent_note = mock_post_instance.post.call_args.kwargs["json"].object
    assert "https://www.w3.org/ns/activitystreams#Public" in sent_note.to
    assert author_url in sent_note.cc


@pytest.mark.asyncio
async def test_handle_create_reply_has_mention_tag():
    """Note de resposta tem tag de Mention com href do autor."""
    author_url = "https://mastodon.social/users/fulano"
    activity = _build_activity(_note_with_mention("Hello"), actor_url=author_url)
    remote_actor = _make_remote_actor(author_url)
    mock_fetch_client, mock_post_client = _mock_ap_client(remote_actor)

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "en"}),
        ),
        patch.object(
            worker_module, "ActivityPubClient", side_effect=[mock_fetch_client, mock_post_client]
        ),
        patch.object(worker_module, "get_bot_keys", AsyncMock(return_value=[_make_actor_key()])),
    ):
        await worker_module.handle_create(activity)

    mock_post_instance = mock_post_client.__aenter__.return_value
    sent_note = mock_post_instance.post.call_args.kwargs["json"].object
    mention_tags = [t for t in sent_note.tag if getattr(t, "type", None) == "Mention"]
    assert len(mention_tags) == 1
    assert mention_tags[0].href == author_url


@pytest.mark.asyncio
async def test_handle_create_uses_draft_cavage_signing():
    """client.post é chamado com sign_with=['draft-cavage'] e signatures."""
    activity = _build_activity(_note_with_mention("Hello"))
    remote_actor = _make_remote_actor()
    mock_fetch_client, mock_post_client = _mock_ap_client(remote_actor)

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "en"}),
        ),
        patch.object(
            worker_module, "ActivityPubClient", side_effect=[mock_fetch_client, mock_post_client]
        ),
        patch.object(worker_module, "get_bot_keys", AsyncMock(return_value=[_make_actor_key()])),
    ):
        await worker_module.handle_create(activity)

    mock_post_instance = mock_post_client.__aenter__.return_value
    call_kwargs = mock_post_instance.post.call_args.kwargs
    assert call_kwargs["sign_with"] == ["draft-cavage"]
    assert "signatures" in call_kwargs


@pytest.mark.asyncio
async def test_handle_create_ignores_post_without_mention():
    activity = _build_activity(_note_without_mention())

    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "translate_text") as mock_translate:
        await worker_module.handle_create(activity)

    mock_translate.assert_not_called()


@pytest.mark.asyncio
async def test_handle_create_ignores_empty_text_after_stripping_mention():
    note = Note(
        id="https://mastodon.social/statuses/3",
        attributed_to="https://mastodon.social/users/fulano",
        content='<p><span class="mention"><a href="https://bot.test/users/testbot">@testbot</a></span></p>',
        tag=[{"type": "Mention", "href": "https://bot.test/users/testbot", "name": "@testbot"}],
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )
    activity = _build_activity(note)

    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "translate_text") as mock_translate:
        await worker_module.handle_create(activity)

    mock_translate.assert_not_called()


# ---------------------------------------------------------------------------
# Detecção de menção via tag Mention estruturada, não substring no HTML
# (issue #14)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_create_ignores_bot_url_in_content_without_mention_tag():
    """
    Falso positivo da lógica antiga: a URL do bot aparece no texto (ex: um
    link citado), mas não há tag Mention real apontando pra ela — não deve
    responder.
    """
    note = Note(
        id="https://mastodon.social/statuses/50",
        attributed_to="https://mastodon.social/users/fulano",
        content="<p>Olha esse bot legal: https://bot.test/users/testbot</p>",
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )
    activity = _build_activity(note)

    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "translate_text") as mock_translate:
        await worker_module.handle_create(activity)

    mock_translate.assert_not_called()


@pytest.mark.asyncio
async def test_handle_create_ignores_mention_tag_pointing_to_other_actor():
    """Tag Mention existe mas aponta pra outro ator — mesmo com a URL do bot no HTML, não deve responder."""
    note = Note(
        id="https://mastodon.social/statuses/51",
        attributed_to="https://mastodon.social/users/fulano",
        content=(
            '<p><span class="mention">'
            '<a href="https://bot.test/users/testbot">@testbot</a>'
            "</span> oi</p>"
        ),
        tag=[
            {
                "type": "Mention",
                "href": "https://mastodon.social/users/outrapessoa",
                "name": "@outrapessoa",
            }
        ],
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )
    activity = _build_activity(note)

    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "translate_text") as mock_translate:
        await worker_module.handle_create(activity)

    mock_translate.assert_not_called()


@pytest.mark.asyncio
async def test_handle_create_detects_mention_via_tag_without_url_in_content():
    """
    Falso negativo da lógica antiga: a tag Mention aponta pro bot mesmo sem
    a URL aparecer literalmente no HTML (formatação diferente entre
    implementações) — deve responder.
    """
    note = Note(
        id="https://mastodon.social/statuses/52",
        attributed_to="https://mastodon.social/users/fulano",
        content='<p><span class="h-card"><a href="/@testbot">@testbot</a></span> Bonjour</p>',
        tag=[{"type": "Mention", "href": "https://bot.test/users/testbot", "name": "@testbot"}],
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )
    activity = _build_activity(note)
    remote_actor = _make_remote_actor()
    mock_fetch_client, mock_post_client = _mock_ap_client(remote_actor)

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "fr"}),
        ) as mock_translate,
        patch.object(
            worker_module, "ActivityPubClient", side_effect=[mock_fetch_client, mock_post_client]
        ),
        patch.object(worker_module, "get_bot_keys", AsyncMock(return_value=[_make_actor_key()])),
    ):
        await worker_module.handle_create(activity)

    mock_translate.assert_called_once()


def test_mentions_bot_matches_raw_dict_tag():
    """
    _mentions_bot também reconhece a tag como dict puro — o pydantic do Note
    coage dicts pra um tipo de objeto (ver testes acima), mas isso não é
    garantido em todo caminho de construção do Note.
    """
    from workers.inbox_worker import _mentions_bot

    tags = [{"type": "Mention", "href": "https://bot.test/users/testbot", "name": "@testbot"}]
    assert _mentions_bot(tags, "https://bot.test/users/testbot") is True


def test_mentions_bot_ignores_raw_dict_tag_for_other_actor():
    from workers.inbox_worker import _mentions_bot

    tags = [{"type": "Mention", "href": "https://mastodon.social/users/outrapessoa", "name": "@x"}]
    assert _mentions_bot(tags, "https://bot.test/users/testbot") is False


@pytest.mark.asyncio
async def test_handle_create_ignores_non_note_object():
    non_note = MagicMock()
    non_note.__class__ = object

    activity = MagicMock(spec=Create)
    activity.id = "https://mastodon.social/statuses/1/activity"
    activity.actor = "https://mastodon.social/users/fulano"
    activity.object = non_note

    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "translate_text") as mock_translate:
        await worker_module.handle_create(activity)

    mock_translate.assert_not_called()


@pytest.mark.asyncio
async def test_handle_create_logs_error_on_send_failure():
    """Erros no envio são logados mas não propagados."""
    activity = _build_activity(_note_with_mention("Bonjour"))
    remote_actor = _make_remote_actor()
    mock_fetch_client, mock_post_client = _mock_ap_client(remote_actor)

    # simula falha no post
    mock_post_client.__aenter__.return_value.post.side_effect = Exception("connection refused")

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "fr"}),
        ),
        patch.object(
            worker_module, "ActivityPubClient", side_effect=[mock_fetch_client, mock_post_client]
        ),
        patch.object(worker_module, "get_bot_keys", AsyncMock(return_value=[_make_actor_key()])),
        patch.object(worker_module, "log") as mock_log,
    ):
        await worker_module.handle_create(activity)

    mock_log.error.assert_called_once()
    assert "connection refused" in str(mock_log.error.call_args)


@pytest.mark.asyncio
async def test_handle_create_skips_when_already_processed(mock_already_processed):
    """Se activity.id já foi processado (reentrega), handle_create não traduz nem responde."""
    activity = _build_activity(_note_with_mention("Bonjour"))
    mock_already_processed.return_value = True

    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "translate_text") as mock_translate:
        await worker_module.handle_create(activity)

    mock_already_processed.assert_awaited_once_with(activity.id)
    mock_translate.assert_not_called()


@pytest.mark.asyncio
async def test_handle_create_marks_processed_after_successful_delivery(mock_mark_processed):
    """Após entregar a resposta com sucesso, a atividade é marcada como processada."""
    activity = _build_activity(_note_with_mention("Bonjour"))
    remote_actor = _make_remote_actor()
    mock_fetch_client, mock_post_client = _mock_ap_client(remote_actor)

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "fr"}),
        ),
        patch.object(
            worker_module, "ActivityPubClient", side_effect=[mock_fetch_client, mock_post_client]
        ),
        patch.object(worker_module, "get_bot_keys", AsyncMock(return_value=[_make_actor_key()])),
    ):
        await worker_module.handle_create(activity)

    mock_mark_processed.assert_awaited_once_with(activity.id)


@pytest.mark.asyncio
async def test_handle_create_does_not_mark_processed_when_delivery_fails(mock_mark_processed):
    """Se a entrega falhar, a atividade NÃO é marcada — permite retry legítimo na reentrega."""
    activity = _build_activity(_note_with_mention("Bonjour"))
    remote_actor = _make_remote_actor()
    mock_fetch_client, mock_post_client = _mock_ap_client(remote_actor)
    mock_post_client.__aenter__.return_value.post.side_effect = Exception("connection refused")

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "fr"}),
        ),
        patch.object(
            worker_module, "ActivityPubClient", side_effect=[mock_fetch_client, mock_post_client]
        ),
        patch.object(worker_module, "get_bot_keys", AsyncMock(return_value=[_make_actor_key()])),
    ):
        await worker_module.handle_create(activity)

    mock_mark_processed.assert_not_called()


@pytest.mark.asyncio
async def test_run_worker_processes_activity_from_queue(mock_dequeue):
    """run_worker consome (row_id, activity) da fila (não ctx)."""
    activity = _build_activity(_note_without_mention())
    test_queue: asyncio.Queue = asyncio.Queue()
    await test_queue.put((42, activity))

    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "handle_create", AsyncMock()) as mock_handle:
        worker_module.activity_queue = test_queue
        task = asyncio.create_task(worker_module.run_worker())
        await test_queue.join()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    mock_handle.assert_called_once_with(activity)


@pytest.mark.asyncio
async def test_run_worker_dequeues_after_successful_processing(mock_dequeue):
    """Após handle_create ter sucesso, o item é removido da persistência (dequeue)."""
    activity = _build_activity(_note_without_mention())
    test_queue: asyncio.Queue = asyncio.Queue()
    await test_queue.put((42, activity))

    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "handle_create", AsyncMock()):
        worker_module.activity_queue = test_queue
        task = asyncio.create_task(worker_module.run_worker())
        await test_queue.join()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    mock_dequeue.assert_called_once_with(42)


@pytest.mark.asyncio
async def test_run_worker_does_not_dequeue_when_handle_create_fails(mock_dequeue):
    """Se handle_create falhar, o item NÃO é removido — fica para retry no próximo restart."""
    activity = _build_activity(_note_without_mention())
    test_queue: asyncio.Queue = asyncio.Queue()
    await test_queue.put((42, activity))

    import workers.inbox_worker as worker_module

    with patch.object(
        worker_module, "handle_create", AsyncMock(side_effect=RuntimeError("falhou"))
    ):
        worker_module.activity_queue = test_queue
        task = asyncio.create_task(worker_module.run_worker())
        await test_queue.join()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    mock_dequeue.assert_not_called()


@pytest.mark.asyncio
async def test_run_worker_calls_load_pending_on_startup(mock_load_pending):
    """run_worker recarrega itens pendentes de uma execução anterior no startup."""
    import workers.inbox_worker as worker_module

    worker_module.activity_queue = asyncio.Queue()
    task = asyncio.create_task(worker_module.run_worker())
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    mock_load_pending.assert_called_once()


@pytest.mark.asyncio
async def test_handle_create_truncates_long_text():
    """Texto acima de 500 caracteres deve ser truncado antes de ser traduzido."""
    long_text = "A" * 600
    note = Note(
        id="https://mastodon.social/statuses/10",
        attributed_to="https://mastodon.social/users/fulano",
        content=(
            '<p><span class="mention">'
            '<a href="https://bot.test/users/testbot">@testbot</a>'
            f"</span> {long_text}</p>"
        ),
        tag=[{"type": "Mention", "href": "https://bot.test/users/testbot", "name": "@testbot"}],
        to=["https://www.w3.org/ns/activitystreams#Public"],
    )
    activity = _build_activity(note)
    remote_actor = _make_remote_actor()
    mock_fetch_client, mock_post_client = _mock_ap_client(remote_actor)

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Texto traduzido", "detected_source": "en"}),
        ) as mock_translate,
        patch.object(
            worker_module, "ActivityPubClient", side_effect=[mock_fetch_client, mock_post_client]
        ),
        patch.object(worker_module, "get_bot_keys", AsyncMock(return_value=[_make_actor_key()])),
    ):
        await worker_module.handle_create(activity)

    translated_text = mock_translate.call_args[0][0]
    assert len(translated_text) == 500


@pytest.mark.asyncio
async def test_handle_create_ignores_invalid_actor_url():
    """Actor com URL inválida (sem scheme/netloc) → não tenta buscar actor remoto."""
    activity = _build_activity(_note_with_mention("Hello"), actor_url="not-a-valid-url")

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "en"}),
        ),
        patch.object(worker_module, "ActivityPubClient") as mock_ap_client,
    ):
        await worker_module.handle_create(activity)

    mock_ap_client.assert_not_called()


@pytest.mark.asyncio
async def test_handle_create_logs_error_when_actor_fetch_fails():
    """Falha ao buscar actor remoto → erro logado, sem propagar exceção."""
    activity = _build_activity(_note_with_mention("Hello"))

    mock_fetch_instance = MagicMock()
    mock_fetch_instance.actor.fetch = AsyncMock(side_effect=Exception("connection refused"))
    mock_fetch_client = AsyncMock()
    mock_fetch_client.__aenter__ = AsyncMock(return_value=mock_fetch_instance)
    mock_fetch_client.__aexit__ = AsyncMock(return_value=False)

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "en"}),
        ),
        patch.object(worker_module, "ActivityPubClient", return_value=mock_fetch_client),
        patch.object(worker_module, "log") as mock_log,
    ):
        await worker_module.handle_create(activity)

    mock_log.error.assert_called_once()
    assert "connection refused" in str(mock_log.error.call_args)


@pytest.mark.asyncio
async def test_handle_create_logs_error_when_no_rsa_key():
    """Quando nenhuma chave RSA está disponível, loga erro e não envia resposta."""
    non_rsa_key = MagicMock(spec=ActorKey)
    non_rsa_key.private_key = MagicMock()  # não é rsa_module.RSAPrivateKey

    activity = _build_activity(_note_with_mention("Hello"))
    remote_actor = _make_remote_actor()
    mock_fetch_client, mock_post_client = _mock_ap_client(remote_actor)

    import workers.inbox_worker as worker_module

    with (
        patch.object(
            worker_module,
            "translate_text",
            AsyncMock(return_value={"translated": "Olá", "detected_source": "en"}),
        ),
        patch.object(
            worker_module, "ActivityPubClient", side_effect=[mock_fetch_client, mock_post_client]
        ),
        patch.object(worker_module, "get_bot_keys", AsyncMock(return_value=[non_rsa_key])),
        patch.object(worker_module, "log") as mock_log,
    ):
        await worker_module.handle_create(activity)

    mock_log.error.assert_called_once()
    mock_post_client.__aenter__.return_value.post.assert_not_called()


@pytest.mark.asyncio
async def test_run_worker_continues_after_error():
    """run_worker processa o segundo item mesmo que o primeiro falhe."""
    activity1 = _build_activity(_note_without_mention())
    activity2 = _build_activity(_note_without_mention())

    test_queue: asyncio.Queue = asyncio.Queue()
    await test_queue.put((1, activity1))
    await test_queue.put((2, activity2))

    call_count = 0

    async def handle_side_effect(activity):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Erro simulado no primeiro item")

    import workers.inbox_worker as worker_module

    with patch.object(worker_module, "handle_create", side_effect=handle_side_effect):
        worker_module.activity_queue = test_queue
        task = asyncio.create_task(worker_module.run_worker())
        await asyncio.sleep(0.2)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert call_count == 2
