"""
workers/inbox_worker.py

Worker assíncrono que processa atividades Create recebidas no inbox do bot.

Fluxo:
1. Consome atividades da fila (activity_queue)
2. Verifica se o bot foi mencionado no post
3. Extrai o texto puro removendo tags HTML
4. Traduz via Google Translate
5. Monta um Note de resposta e entrega no inbox do autor
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from apkit.client.asyncio.client import ActivityPubClient
from apkit.models import Create, Note
from apkit.types import ActorKey
from bs4 import BeautifulSoup
from cryptography.hazmat.primitives.asymmetric import rsa as rsa_module

from app.activitypub.keys import get_bot_keys
from app.config import settings
from app.services.queue import activity_queue
from app.services.translate import translate_text

log = logging.getLogger(__name__)


async def handle_create(activity: Create) -> None:
    note = activity.object

    log.info(
        f"handle_create: actor={activity.actor}, "
        f"note_content={getattr(note, 'content', None)}"
    )

    if not isinstance(note, Note):
        return

    bot_actor_url = f"https://{settings.domain}/users/{settings.bot_username}"
    content_html = note.content or ""

    if bot_actor_url not in content_html:
        return

    # Extrai texto puro removendo a menção ao bot
    soup = BeautifulSoup(content_html, "html.parser")
    for tag in soup.find_all("span", {"class": "mention"}):
        tag.decompose()
    plain_text = soup.get_text(separator=" ").strip()

    if not plain_text:
        return

    # Traduz o texto
    result = await translate_text(plain_text)
    translated = result["translated"]
    source_lang = result["detected_source"].upper()
    target_lang = settings.target_language.upper()

    # Dados do autor
    author_url = (
        activity.actor if isinstance(activity.actor, str) else activity.actor.id
    )
    author_username = author_url.rstrip("/").split("/")[-1]
    author_domain = author_url.split("/")[2]

    # Busca o actor remoto
    async with ActivityPubClient() as client:
        remote_actor = await client.actor.fetch(author_url)

    # Monta o HTML de resposta
    reply_html = (
        f'<p><span class="h-card"><a href="{author_url}">@{author_username}</a></span> '
        f"🌐 <strong>[{source_lang} → {target_lang}]</strong><br>"
        f"{translated}</p>"
    )

    # IDs únicos
    note_id = (
        f"https://{settings.domain}/users/{settings.bot_username}"
        f"/notes/{uuid.uuid4()}"
    )
    create_id = (
        f"https://{settings.domain}/users/{settings.bot_username}"
        f"/creates/{uuid.uuid4()}"
    )

    reply_note = Note(
        id=note_id,
        attributed_to=bot_actor_url,
        content=reply_html,
        to=[author_url],
        cc=["https://www.w3.org/ns/activitystreams#Public"],
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

    reply_create = Create(
        id=create_id,
        actor=bot_actor_url,
        object=reply_note,
        to=[author_url],
        cc=["https://www.w3.org/ns/activitystreams#Public"],
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
    except Exception as e:
        log.error(f"Erro ao entregar resposta para {author_url}: {e}", exc_info=True)


async def run_worker() -> None:
    log.info("Worker de inbox iniciado")
    while True:
        try:
            ctx = await asyncio.wait_for(activity_queue.get(), timeout=5.0)
            await handle_create(ctx)
            activity_queue.task_done()
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            log.error(f"Erro no worker: {e}", exc_info=True)
