import asyncio
import logging
from bs4 import BeautifulSoup

from apkit.models import Note, Create
from apkit.client.asyncio.client import ActivityPubClient

from app.config import settings
from app.activitypub.actor import build_actor
from app.activitypub.keys import get_keys_for_actor
from app.services.queue import activity_queue
from app.services.translate import translate_text

log = logging.getLogger(__name__)


async def handle_create(ctx) -> None:
    activity: Create = ctx.activity
    note = activity.object

    if not isinstance(note, Note):
        return

    bot_mention  = f"@{settings.bot_username}@{settings.domain}"
    content_html = note.content or ""

    if bot_mention not in content_html:
        return

    # Extrai texto puro removendo a menção ao bot
    soup = BeautifulSoup(content_html, "html.parser")
    for tag in soup.find_all("span", {"class": "mention"}):
        tag.decompose()
    plain_text = soup.get_text(separator=" ").strip()

    if not plain_text:
        return

    result      = await translate_text(plain_text)
    translated  = result["translated"]
    source_lang = result["detected_source"].upper()
    target_lang = settings.target_language.upper()

    author_url      = activity.actor if isinstance(activity.actor, str) else activity.actor.id
    author_username = author_url.rstrip("/").split("/")[-1]
    actor           = build_actor()

    reply_content = (
        f'<p><span class="h-card"><a href="{author_url}">@{author_username}</a></span> '
        f"🌐 <strong>[{source_lang} → {target_lang}]</strong><br>"
        f"{translated}</p>"
    )

    reply_note = Note(
        attributedTo=actor.id,
        inReplyTo={"id": note.id, "type": "Note"},
        to=[author_url],
        cc=["https://www.w3.org/ns/activitystreams#Public"],
        content=reply_content,
    )

    reply_create = Create(
        actor=actor.id,
        object=reply_note,
        to=reply_note.to,
        cc=reply_note.cc,
    )

    async with ActivityPubClient() as client:
        remote_actor = await client.actor.fetch(author_url)

    await ctx.send(get_keys_for_actor, remote_actor, reply_create)
    log.info(f"Tradução [{source_lang}→{target_lang}] enviada para {author_url}")


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
