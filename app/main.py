import asyncio
import logging
from contextlib import asynccontextmanager

from apkit.client import WebfingerLink, WebfingerResource, WebfingerResult
from apkit.models import (
    Nodeinfo, NodeinfoServices, NodeinfoSoftware, NodeinfoUsage, NodeinfoUsageUsers,
)
from apkit.server.app import ActivityPubServer
from apkit.server.responses import ActivityResponse
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.activitypub.actor import build_actor
from app.activitypub.handlers import register_handlers
from app.config import settings

logging.basicConfig(level=logging.INFO)

actor = build_actor()


@asynccontextmanager
async def lifespan(app):
    import app.database
    import workers.inbox_worker
    await app.database.init_db()
    worker_task = asyncio.create_task(workers.inbox_worker.run_worker())
    yield
    worker_task.cancel()


api = ActivityPubServer(lifespan=lifespan)
register_handlers(api)
api.inbox("/users/{identifier}/inbox")


@api.get("/users/{identifier}")
async def get_actor(identifier: str):
    if identifier == settings.bot_username:
        return ActivityResponse(actor)
    return JSONResponse({"error": "Not found"}, status_code=404)


@api.webfinger()
async def webfinger(request: Request, acct: WebfingerResource) -> Response:
    if acct.username == settings.bot_username and acct.host == settings.domain:
        link = WebfingerLink(
            rel="self",
            type="application/activity+json",
            href=f"https://{settings.domain}/users/{settings.bot_username}",
        )
        result = WebfingerResult(subject=acct, links=[link])
        return JSONResponse(result.to_json(), media_type="application/jrd+json")
    return JSONResponse({"error": "Not found"}, status_code=404)


@api.nodeinfo("/nodeinfo/2.1", "2.1")
async def nodeinfo():
    return ActivityResponse(
        Nodeinfo(
            version="2.1",
            software=NodeinfoSoftware(name="translate-bot", version="1.0.0"),
            protocols=["activitypub"],
            services=NodeinfoServices(inbound=[], outbound=[]),
            openRegistrations=False,
            usage=NodeinfoUsage(users=NodeinfoUsageUsers(total=1)),
            metadata={},
        )
    )


@api.get("/users/{identifier}/followers")
async def get_followers(identifier: str):
    if identifier != settings.bot_username:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse({
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"https://{settings.domain}/users/{identifier}/followers",
        "type": "OrderedCollection",
        "totalItems": 0,
        "orderedItems": [],
    }, media_type="application/activity+json")


@api.get("/users/{identifier}/outbox")
async def get_outbox(identifier: str):
    if identifier != settings.bot_username:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse({
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"https://{settings.domain}/users/{identifier}/outbox",
        "type": "OrderedCollection",
        "totalItems": 0,
        "orderedItems": [],
    }, media_type="application/activity+json")

@api.get("/health")
async def health():
    return {"status": "ok"}
