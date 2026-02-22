"""
Testes para app/main.py

Testa os endpoints HTTP diretamente via httpx.AsyncClient + ASGITransport,
que é a forma recomendada para testar apps FastAPI/Starlette assíncronos.

Cobre:
- GET /users/{username}               → 200 com Actor JSON-LD do bot
- GET /users/{username}               → 404 para username desconhecido
- GET /users/{username}/followers     → 200 com OrderedCollection vazia
- GET /users/{username}/followers     → 404 para username desconhecido
- GET /users/{username}/outbox        → 200 com OrderedCollection vazia
- GET /users/{username}/outbox        → 404 para username desconhecido
- GET /.well-known/webfinger          → 200 com JRD correto para o bot
- GET /.well-known/webfinger          → 404 para conta desconhecida
- GET /.well-known/webfinger          → 404 para domínio errado
- GET /nodeinfo/2.1                   → 200 com NodeInfo válido
- GET /health                         → 200 com {"status": "ok"}
- Lifespan: init_db é chamado no startup
- Lifespan: run_worker é iniciado no startup
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Fixture do cliente de teste
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    with (
        patch("app.database.init_db", AsyncMock()),
        patch("workers.inbox_worker.run_worker", AsyncMock()),
    ):
        from app.main import api

        async with AsyncClient(
            transport=ASGITransport(app=api),
            base_url="https://bot.test",
        ) as ac:
            yield ac


# ---------------------------------------------------------------------------
# GET /users/{identifier}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_actor_returns_200_for_bot(client):
    response = await client.get("/users/testbot")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_actor_content_type(client):
    response = await client.get("/users/testbot")
    assert "application/activity+json" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_get_actor_body_has_correct_id(client):
    response = await client.get("/users/testbot")
    data = response.json()
    assert data["id"] == "https://bot.test/users/testbot"


@pytest.mark.asyncio
async def test_get_actor_body_has_inbox(client):
    response = await client.get("/users/testbot")
    data = response.json()
    assert data["inbox"] == "https://bot.test/users/testbot/inbox"


@pytest.mark.asyncio
async def test_get_actor_body_has_followers_url(client):
    """Actor deve declarar o endpoint de followers."""
    response = await client.get("/users/testbot")
    data = response.json()
    assert data["followers"] == "https://bot.test/users/testbot/followers"


@pytest.mark.asyncio
async def test_get_actor_body_has_outbox_url(client):
    """Actor deve declarar o endpoint de outbox."""
    response = await client.get("/users/testbot")
    data = response.json()
    assert data["outbox"] == "https://bot.test/users/testbot/outbox"


@pytest.mark.asyncio
async def test_get_actor_body_has_public_key(client):
    response = await client.get("/users/testbot")
    data = response.json()
    assert "publicKey" in data
    assert "publicKeyPem" in data["publicKey"]
    assert "BEGIN PUBLIC KEY" in data["publicKey"]["publicKeyPem"]


@pytest.mark.asyncio
async def test_get_actor_returns_404_for_unknown_user(client):
    response = await client.get("/users/outrobot")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /users/{identifier}/followers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_followers_returns_200_for_bot(client):
    response = await client.get("/users/testbot/followers")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_followers_content_type(client):
    response = await client.get("/users/testbot/followers")
    assert "application/activity+json" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_get_followers_body_is_ordered_collection(client):
    response = await client.get("/users/testbot/followers")
    data = response.json()
    assert data["type"] == "OrderedCollection"


@pytest.mark.asyncio
async def test_get_followers_body_has_correct_id(client):
    response = await client.get("/users/testbot/followers")
    data = response.json()
    assert data["id"] == "https://bot.test/users/testbot/followers"


@pytest.mark.asyncio
async def test_get_followers_body_has_context(client):
    response = await client.get("/users/testbot/followers")
    data = response.json()
    assert data["@context"] == "https://www.w3.org/ns/activitystreams"


@pytest.mark.asyncio
async def test_get_followers_returns_404_for_unknown_user(client):
    response = await client.get("/users/outrobot/followers")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /users/{identifier}/outbox
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_outbox_returns_200_for_bot(client):
    response = await client.get("/users/testbot/outbox")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_outbox_content_type(client):
    response = await client.get("/users/testbot/outbox")
    assert "application/activity+json" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_get_outbox_body_is_ordered_collection(client):
    response = await client.get("/users/testbot/outbox")
    data = response.json()
    assert data["type"] == "OrderedCollection"


@pytest.mark.asyncio
async def test_get_outbox_body_has_correct_id(client):
    response = await client.get("/users/testbot/outbox")
    data = response.json()
    assert data["id"] == "https://bot.test/users/testbot/outbox"


@pytest.mark.asyncio
async def test_get_outbox_body_has_context(client):
    response = await client.get("/users/testbot/outbox")
    data = response.json()
    assert data["@context"] == "https://www.w3.org/ns/activitystreams"


@pytest.mark.asyncio
async def test_get_outbox_returns_404_for_unknown_user(client):
    response = await client.get("/users/outrobot/outbox")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /.well-known/webfinger
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webfinger_returns_200_for_bot(client):
    response = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:testbot@bot.test"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_webfinger_content_type(client):
    response = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:testbot@bot.test"},
    )
    assert "application/jrd+json" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_webfinger_body_has_subject(client):
    response = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:testbot@bot.test"},
    )
    data = response.json()
    assert data["subject"] == "acct:testbot@bot.test"


@pytest.mark.asyncio
async def test_webfinger_body_has_self_link(client):
    response = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:testbot@bot.test"},
    )
    data = response.json()
    self_links = [link for link in data["links"] if link["rel"] == "self"]
    assert len(self_links) == 1
    assert self_links[0]["href"] == "https://bot.test/users/testbot"
    assert self_links[0]["type"] == "application/activity+json"


@pytest.mark.asyncio
async def test_webfinger_returns_404_for_unknown_user(client):
    response = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:fantasma@bot.test"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_webfinger_returns_404_for_wrong_domain(client):
    response = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:testbot@outro.dominio.com"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /nodeinfo/2.1
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nodeinfo_returns_200(client):
    response = await client.get("/nodeinfo/2.1")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_nodeinfo_version(client):
    response = await client.get("/nodeinfo/2.1")
    data = response.json()
    assert data["version"] == "2.1"


@pytest.mark.asyncio
async def test_nodeinfo_software_name(client):
    response = await client.get("/nodeinfo/2.1")
    data = response.json()
    assert data["software"]["name"] == "translate-bot"


@pytest.mark.asyncio
async def test_nodeinfo_protocols(client):
    response = await client.get("/nodeinfo/2.1")
    data = response.json()
    assert "activitypub" in data["protocols"]


@pytest.mark.asyncio
async def test_nodeinfo_open_registrations(client):
    response = await client.get("/nodeinfo/2.1")
    data = response.json()
    assert data["openRegistrations"] is False


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_body(client):
    response = await client.get("/health")
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Lifespan: inicialização e shutdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lifespan_calls_init_db():
    mock_init_db = AsyncMock()

    import sys

    sys.modules.pop("app.main", None)

    with (
        patch("app.database.init_db", mock_init_db),
        patch("workers.inbox_worker.run_worker", AsyncMock()),
    ):
        from app.main import api

        async with LifespanManager(api):
            pass

    mock_init_db.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_starts_worker():
    mock_run_worker = AsyncMock()

    import sys

    sys.modules.pop("app.main", None)

    with (
        patch("app.database.init_db", AsyncMock()),
        patch("workers.inbox_worker.run_worker", mock_run_worker),
    ):
        from app.main import api

        async with LifespanManager(api):
            pass

    mock_run_worker.assert_called_once()
