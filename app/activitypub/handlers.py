import logging
from fastapi import Response
from fastapi.responses import JSONResponse

from apkit.server.types import Context
from apkit.models import Follow, Create, Accept, Actor as APKitActor
from apkit.client.asyncio.client import ActivityPubClient

from app.activitypub.actor import build_actor
from app.services import queue as queue_module
from app.activitypub.keys import get_keys_for_actor

log = logging.getLogger(__name__)


def register_handlers(app) -> None:
    """
    Registra os handlers de atividades no servidor apkit.
    Chamado em main.py após criar a instância ActivityPubServer.
    """

    @app.on(Follow)
    async def on_follow(ctx: Context):
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

        await ctx.send(get_keys_for_actor, follower_actor, accept)
        log.info(f"Follow aceito de {follower_actor.id}")
        return Response(status_code=202)

    @app.on(Create)
    async def on_create(ctx: Context):
        """
        Enfileira para o worker assíncrono e retorna 202 imediatamente.
        Mastodon tem timeout curto — nunca bloquear no handler.
        """
        await queue_module.activity_queue.put(ctx)
        return Response(status_code=202)
    