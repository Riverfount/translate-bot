"""
Testes para app/main.py

Testa os endpoints HTTP diretamente via httpx.AsyncClient + ASGITransport,
que é a forma recomendada para testar apps FastAPI/Starlette assíncronos.

Cobre:
- GET /users/{username}       → 200 com Actor JSON-LD do bot
- GET /users/{username}       → 404 para username desconhecido
- GET /.well-known/webfinger  → 200 com JRD correto para o bot
- GET /.well-known/webfinger  → 404 para conta desconhecida
- GET /.well-known/webfinger  → 404 para domínio errado
- GET /nodeinfo/2.1           → 200 com NodeInfo válido
- GET /health                 → 200 com {"status": "ok"}
- Lifespan: init_db é chamado no startup
- Lifespan: run_worker é iniciado no startup
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport


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
    """Deve retornar 200 com o Actor JSON-LD do bot."""
    response = await client.get("/users/testbot")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_actor_content_type(client):
    """Deve retornar Content-Type application/activity+json."""
    response = await client.get("/users/testbot")

    assert "application/activity+json" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_get_actor_body_has_correct_id(client):
    """O campo `id` do Actor deve corresponder à URL canônica do bot."""
    response = await client.get("/users/testbot")
    data = response.json()

    assert data["id"] == "https://bot.test/users/testbot"


@pytest.mark.asyncio
async def test_get_actor_body_has_inbox(client):
    """O Actor deve expor o campo `inbox`."""
    response = await client.get("/users/testbot")
    data = response.json()

    assert data["inbox"] == "https://bot.test/users/testbot/inbox"


@pytest.mark.asyncio
async def test_get_actor_body_has_public_key(client):
    """O Actor deve expor a chave pública no campo `publicKey`."""
    response = await client.get("/users/testbot")
    data = response.json()

    assert "publicKey" in data
    assert "publicKeyPem" in data["publicKey"]
    assert "BEGIN PUBLIC KEY" in data["publicKey"]["publicKeyPem"]


@pytest.mark.asyncio
async def test_get_actor_returns_404_for_unknown_user(client):
    """Deve retornar 404 para qualquer username que não seja o bot."""
    response = await client.get("/users/outrobot")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /.well-known/webfinger
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_webfinger_returns_200_for_bot(client):
    """Deve retornar 200 para a conta correta do bot."""
    response = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:testbot@bot.test"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_webfinger_content_type(client):
    """Deve retornar Content-Type application/jrd+json."""
    response = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:testbot@bot.test"},
    )

    assert "application/jrd+json" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_webfinger_body_has_subject(client):
    """O corpo deve conter o campo `subject` com a conta solicitada."""
    response = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:testbot@bot.test"},
    )
    data = response.json()

    assert data["subject"] == "acct:testbot@bot.test"


@pytest.mark.asyncio
async def test_webfinger_body_has_self_link(client):
    """Deve conter um link `rel=self` apontando para o Actor."""
    response = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:testbot@bot.test"},
    )
    data = response.json()

    self_links = [l for l in data["links"] if l["rel"] == "self"]
    assert len(self_links) == 1
    assert self_links[0]["href"] == "https://bot.test/users/testbot"
    assert self_links[0]["type"] == "application/activity+json"


@pytest.mark.asyncio
async def test_webfinger_returns_404_for_unknown_user(client):
    """Deve retornar 404 para username que não existe."""
    response = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:fantasma@bot.test"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_webfinger_returns_404_for_wrong_domain(client):
    """Deve retornar 404 quando o domínio não bate com o settings.domain."""
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
    """O campo `version` deve ser '2.1'."""
    response = await client.get("/nodeinfo/2.1")
    data = response.json()

    assert data["version"] == "2.1"


@pytest.mark.asyncio
async def test_nodeinfo_software_name(client):
    """O nome do software deve ser 'translate-bot'."""
    response = await client.get("/nodeinfo/2.1")
    data = response.json()

    assert data["software"]["name"] == "translate-bot"


@pytest.mark.asyncio
async def test_nodeinfo_protocols(client):
    """Deve declarar suporte ao protocolo ActivityPub."""
    response = await client.get("/nodeinfo/2.1")
    data = response.json()

    assert "activitypub" in data["protocols"]


@pytest.mark.asyncio
async def test_nodeinfo_open_registrations(client):
    """openRegistrations deve ser False — bot não aceita registros."""
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

from asgi_lifespan import LifespanManager


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
