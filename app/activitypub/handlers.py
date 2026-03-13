"""
app/activitypub/handlers.py

Registra os handlers de atividades ActivityPub no servidor apkit.

Handlers:
- Follow  → aceita automaticamente, envia Accept assinado e persiste no banco
- Undo    → remove o follower do banco quando o objeto for um Follow
- Create  → enfileira para o worker assíncrono e retorna 202 imediatamente
"""

import logging

from apkit.client.asyncio.client import ActivityPubClient
from apkit.models import Accept, Actor as APKitActor, Create, Follow, Undo
from apkit.server.types import Context
from fastapi import Response
from fastapi.responses import JSONResponse
from sqlalchemy import delete as sa_delete

from app import database as _db
from app.activitypub.actor import build_actor
from app.activitypub.keys import get_bot_keys
from app.models.follower import Follower as FollowerModel
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
        Resolve o actor remoto, constrói o Accept, envia assinado e persiste o follower.
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

        inbox = follower_actor.inbox
        inbox_url = inbox if isinstance(inbox, str) else (inbox.id if inbox else "")
        async with _db.async_session_factory() as session:
            async with session.begin():
                await session.merge(
                    FollowerModel(actor_url=follower_actor.id, inbox_url=inbox_url or "")
                )

        log.info(f"Follow aceito e persistido: {follower_actor.id}")
        return Response(status_code=202)

    @app.on(Undo)
    async def on_undo(ctx: Context):
        """
        Processa Undo{Follow}: remove o follower do banco.
        Outros tipos de Undo são ignorados silenciosamente.
        """
        activity = ctx.activity
        obj = activity.object

        is_follow_undo = isinstance(obj, Follow) or (
            isinstance(obj, dict) and obj.get("type") == "Follow"
        )
        if not is_follow_undo:
            return Response(status_code=202)

        actor = activity.actor
        if isinstance(actor, str):
            actor_url = actor
        elif isinstance(actor, APKitActor):
            actor_url = actor.id
        else:
            return Response(status_code=202)

        async with _db.async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    sa_delete(FollowerModel).where(FollowerModel.actor_url == actor_url)
                )

        log.info(f"Unfollow processado: {actor_url}")
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
