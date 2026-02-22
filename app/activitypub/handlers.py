"""
app/activitypub/handlers.py

Registra os handlers de atividades ActivityPub no servidor apkit.

Handlers:
- Follow  → aceita automaticamente e envia Accept assinado
- Create  → enfileira para o worker assíncrono e retorna 202 imediatamente
"""

import logging

from apkit.client.asyncio.client import ActivityPubClient
from apkit.models import Accept, Actor as APKitActor, Create, Follow
from apkit.server.types import Context
from fastapi import Response
from fastapi.responses import JSONResponse

from app.activitypub.actor import build_actor
from app.activitypub.keys import get_bot_keys
from app.services import queue as queue_module

log = logging.getLogger(__name__)


def register_handlers(app) -> None:
    """
    Registra os handlers de atividades no servidor apkit.
    Chamado em main.py após criar a instância ActivityPubServer.
    """

    @app.on(Follow)
    async def on_follow(ctx: Context):
        """
        Aceita automaticamente qualquer Follow recebido.
        Resolve o actor remoto, constrói o Accept e envia assinado.
        """
        activity = ctx.activity

        follower_actor = None
        if isinstance(activity.actor, str):
            async with ActivityPubClient() as client:
                follower_actor = await client.actor.fetch(activity.actor)
        elif isinstance(activity.actor, APKitActor):
            follower_actor = activity.actor

        if not follower_actor:
            return JSONResponse({"error": "Could not resolve follower"}, status_code=400)

        actor = build_actor()
        accept = Accept(
            id=f"{actor.id}#accept/{activity.id}",
            actor=actor.id,
            object=activity,
        )

        keys = await get_bot_keys()
        await ctx.send(keys, follower_actor, accept)
        log.info(f"Follow aceito de {follower_actor.id}")
        return Response(status_code=202)

    @app.on(Create)
    async def on_create(ctx: Context):
        """
        Enfileira a atividade para o worker assíncrono e retorna 202 imediatamente.
        Mastodon tem timeout curto — nunca bloquear no handler.

        Enfileira ctx.activity (não ctx) para que o worker não dependa
        do contexto interno do apkit, que não é válido fora do escopo do handler.
        """
        log.info(f"Create recebido de {ctx.activity.actor}")
        await queue_module.activity_queue.put(ctx.activity)
        return Response(status_code=202)
