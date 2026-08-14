"""
workers/inbox_worker.py

Worker assíncrono que processa atividades Create recebidas no inbox do bot.

Fluxo:
1. No startup, recarrega itens pendentes de uma execução anterior
   (load_pending, chamado uma única vez) e inicia N loops consumidores
   em paralelo sobre a mesma fila (settings.worker_concurrency) — um
   item lento não bloqueia o processamento dos demais
2. Cada loop consome atividades da fila (activity_queue)
3. Ignora a atividade se activity.id já foi processado (reentrega do
   Mastodon após uma resposta já enviada com sucesso)
4. Verifica se o bot foi mencionado via a tag Mention estruturada do Note
   (não por substring no HTML — ver _mentions_bot)
5. Extrai o texto puro removendo tags HTML
6. Ignora a menção se o autor está em cooldown (rate limit por ator —
   evita spam público e consumo sem limite da API de tradução)
7. Traduz via LibreTranslate
8. Monta um Note de resposta e entrega no inbox do autor
9. Marca a atividade como processada (mark_processed) só após entrega
   bem-sucedida — erro não marca, permitindo retry legítimo na reentrega
10. Remove a atividade da persistência (dequeue) só após sucesso —
    erro mantém o item para retry no próximo restart do processo
"""

import asyncio
import html
import logging
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from apkit.client.asyncio.client import ActivityPubClient
from apkit.models import Create, Note
from apkit.types import ActorKey
from bs4 import BeautifulSoup
from cryptography.hazmat.primitives.asymmetric import rsa as rsa_module

from app.activitypub.keys import get_bot_keys
from app.config import settings
from app.services.dedup import already_processed, mark_processed
from app.services.note_store import store_note
from app.services.queue import activity_queue, dequeue, load_pending
from app.services.rate_limit import is_rate_limited, record_request
from app.services.translate import translate_text

log = logging.getLogger(__name__)

MAX_TRANSLATE_CHARS = 500


def _mentions_bot(tags: list[Any], bot_actor_url: str) -> bool:
    """
    Verifica se o bot foi mencionado via a lista estruturada `tag` do Note
    (item do tipo Mention com href apontando pro ator do bot), em vez de
    procurar a URL como substring no HTML do content.

    A checagem é feita via getattr/dict.get em vez de isinstance porque,
    dependendo de como o Note chegou (JSON-LD expandido ou construído
    direto via pydantic), o item pode virar uma instância de Mention, Link,
    Hashtag ou um dict puro — mas sempre expõe type/href do mesmo jeito.
    """
    for tag in tags or []:
        if isinstance(tag, dict):
            tag_type = tag.get("type")
            tag_href = tag.get("href")
        else:
            tag_type = getattr(tag, "type", None)
            tag_href = getattr(tag, "href", None)
        if tag_type == "Mention" and tag_href == bot_actor_url:
            return True
    return False


# Caracteres que não podem ficar sozinhos logo após um corte — sinalizam que
# pertencem ao cluster de grafema anterior (emoji composto, acento
# combinante, seletor de variação, indicador regional de bandeira).
_ZWJ = "‍"
_VARIATION_SELECTORS = {"︎", "️"}
_REGIONAL_INDICATOR_RANGE = range(0x1F1E6, 0x1F1FF + 1)
_SKIN_TONE_MODIFIER_RANGE = range(0x1F3FB, 0x1F3FF + 1)


def _is_grapheme_boundary(text: str, index: int) -> bool:
    """
    Retorna True se cortar `text` logo antes de `index` não quebra um
    cluster de grafema (emoji composto via ZWJ, acento combinante, bandeira,
    modificador de tom de pele). Não é uma implementação completa de
    UAX #29 — cobre os casos mais comuns o suficiente para truncar texto
    de posts sem gerar fragmentos de emoji quebrados.
    """
    if index <= 0 or index >= len(text):
        return True

    before, after = text[index - 1], text[index]

    if unicodedata.combining(after):
        return False
    if after in _VARIATION_SELECTORS:
        return False
    if before == _ZWJ or after == _ZWJ:
        return False
    if ord(after) in _SKIN_TONE_MODIFIER_RANGE:
        return False
    if ord(before) in _REGIONAL_INDICATOR_RANGE and ord(after) in _REGIONAL_INDICATOR_RANGE:
        return False

    return True


def _smart_truncate(text: str, max_chars: int) -> str:
    """
    Trunca `text` em até `max_chars`, sem cortar no meio de uma palavra
    nem de um cluster de grafema (emoji composto, acento, bandeira, etc).

    Corta primeiro no limite de caracteres, recua até o corte cair numa
    fronteira de grafema válida, e então recua até o último espaço — a
    menos que não haja espaço algum no trecho (palavra única muito longa),
    caso em que o corte por grafema é mantido como está.
    """
    if len(text) <= max_chars:
        return text

    cut = max_chars
    while cut > 0 and not _is_grapheme_boundary(text, cut):
        cut -= 1

    truncated = text[:cut]

    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]

    return truncated.rstrip()


async def handle_create(activity: Create) -> None:
    if await already_processed(activity.id):
        log.info(f"Activity já processada anteriormente, ignorando: {activity.id}")
        return

    note = activity.object

    log.info(
        f"handle_create: actor={activity.actor}, note_content={getattr(note, 'content', None)}"
    )

    if not isinstance(note, Note):
        return

    bot_actor_url = f"https://{settings.domain}/users/{settings.bot_username}"
    content_html = note.content or ""

    if not _mentions_bot(note.tag, bot_actor_url):
        return

    # Dados do autor — extraídos cedo para permitir checar o rate limit
    # antes de gastar uma chamada à API de tradução
    author_url = activity.actor if isinstance(activity.actor, str) else activity.actor.id
    parsed_author = urlparse(author_url)
    if not parsed_author.scheme or not parsed_author.netloc:
        log.error(f"URL de actor inválida: {author_url!r}")
        return
    author_domain = parsed_author.netloc
    author_username = parsed_author.path.rstrip("/").split("/")[-1]

    # Extrai texto puro removendo a menção ao bot
    soup = BeautifulSoup(content_html, "html.parser")
    for tag in soup.find_all(class_="mention"):
        tag.decompose()
    plain_text = soup.get_text(separator=" ").strip()

    if not plain_text:
        return

    if await is_rate_limited(author_url):
        log.info(f"Rate limit: ignorando menção de {author_url} (cooldown ativo)")
        return
    await record_request(author_url)

    if len(plain_text) > MAX_TRANSLATE_CHARS:
        log.warning(f"Texto truncado de {len(plain_text)} para {MAX_TRANSLATE_CHARS} caracteres")
        plain_text = _smart_truncate(plain_text, MAX_TRANSLATE_CHARS)

    # Traduz o texto
    result = await translate_text(plain_text)
    translated = result["translated"]
    source_lang = result["detected_source"].upper()
    target_lang = settings.target_language.upper()

    # Busca o actor remoto
    try:
        async with ActivityPubClient() as client:
            remote_actor = await client.actor.fetch(author_url)
    except Exception as e:
        log.error(f"Não foi possível resolver o actor {author_url}: {e}", exc_info=True)
        return

    # Monta o HTML de resposta
    reply_html = (
        f'<p><span class="h-card"><a href="{author_url}">@{author_username}</a></span> '
        f"🌐 <strong>[{source_lang} → {target_lang}]</strong><br>"
        f"{html.escape(translated)}</p>"
        f"<p><small>Powered by libretranslate, fastapi, apkit, activitypub and bolhaverse/bolha.io</small></p>"
    )

    # IDs únicos
    note_id = f"https://{settings.domain}/users/{settings.bot_username}/notes/{uuid.uuid4()}"
    create_id = f"https://{settings.domain}/users/{settings.bot_username}/creates/{uuid.uuid4()}"

    reply_note = Note(
        id=note_id,
        attributed_to=bot_actor_url,
        content=reply_html,
        to=["https://www.w3.org/ns/activitystreams#Public"],
        cc=[author_url],
        in_reply_to={"id": note.id, "type": "Note"},
        published=datetime.now(timezone.utc).isoformat(),
        tag=[
            {
                "type": "Mention",
                "href": author_url,
                "name": f"@{remote_actor.preferred_username}@{author_domain}",
            }
        ],
    )

    await store_note(note_id, reply_note)

    reply_create = Create(
        id=create_id,
        actor=bot_actor_url,
        object=reply_note,
        to=["https://www.w3.org/ns/activitystreams#Public"],
        cc=[author_url],
        published=datetime.now(timezone.utc).isoformat(),
    )

    # Obtém as chaves e extrai a chave privada RSA
    keys = await get_bot_keys()
    priv_key = None
    key_id = None
    for key in keys:
        if isinstance(key.private_key, rsa_module.RSAPrivateKey):
            priv_key = key.private_key
            key_id = key.key_id
            break

    if not priv_key or not key_id:
        log.error("Chave privada RSA não encontrada — não é possível enviar resposta")
        return

    log.info(f"Enviando para {remote_actor.inbox} com key_id={key_id}")
    try:
        async with ActivityPubClient() as client:
            async with client.post(
                remote_actor.inbox,
                json=reply_create,
                signatures=[ActorKey(key_id=key_id, private_key=priv_key)],
                sign_with=["draft-cavage"],
            ) as response:
                body = await response.text()
                log.info(f"Status: {response.status} — Resposta: {body[:500]}")
        log.info(f"Tradução [{source_lang}→{target_lang}] enviada para {author_url}")
        await mark_processed(activity.id)
    except Exception as e:
        log.error(f"Erro ao entregar resposta para {author_url}: {e}", exc_info=True)


DEFAULT_WORKER_CONCURRENCY = 3


async def _worker_loop() -> None:
    while True:
        try:
            row_id, activity = await asyncio.wait_for(activity_queue.get(), timeout=5.0)
        except asyncio.TimeoutError:
            continue

        try:
            await handle_create(activity)
            await dequeue(row_id)
        except Exception as e:
            log.error(f"Erro no worker: {e}", exc_info=True)
        finally:
            activity_queue.task_done()


async def run_worker() -> None:
    """
    Recarrega os itens pendentes de uma execução anterior (uma única vez)
    e então roda N loops consumidores em paralelo sobre a mesma fila —
    um item lento (ex: LibreTranslate instável) não bloqueia os demais.
    N é definido por settings.worker_concurrency.
    """
    log.info("Worker de inbox iniciado")
    await load_pending()

    concurrency = settings.get("worker_concurrency", DEFAULT_WORKER_CONCURRENCY)
    log.info(f"Iniciando {concurrency} workers de inbox em paralelo")
    await asyncio.gather(*[_worker_loop() for _ in range(concurrency)])
