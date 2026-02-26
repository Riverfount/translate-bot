"""
Testes para app/activitypub/actor.py e app/activitypub/keys.py

Cobre:
- build_actor(): estrutura e campos do objeto Person gerado
- build_actor(): URLs construídas a partir do domínio das settings
- build_actor(): chave pública embutida no public_key
- get_keys_for_actor(): retorna ActorKey para o username correto
- get_keys_for_actor(): retorna lista vazia para username desconhecido
- load_private_key(): carrega PEM do disco corretamente
- load_public_key_pem(): carrega PEM do disco corretamente
"""

import pytest
from apkit.models import Person


def test_build_actor_returns_person_instance():
    from app.activitypub.actor import build_actor

    assert isinstance(build_actor(), Person)


def test_build_actor_username_matches_settings():
    from app.activitypub.actor import build_actor

    assert build_actor().preferred_username == "testbot"


def test_build_actor_id_uses_domain_and_username():
    from app.activitypub.actor import build_actor

    assert build_actor().id == "https://bot.test/users/testbot"


def test_build_actor_inbox_url():
    from app.activitypub.actor import build_actor

    assert build_actor().inbox == "https://bot.test/users/testbot/inbox"


def test_build_actor_outbox_url():
    from app.activitypub.actor import build_actor

    assert build_actor().outbox == "https://bot.test/users/testbot/outbox"


def test_build_actor_followers_url():
    from app.activitypub.actor import build_actor

    assert build_actor().followers == "https://bot.test/users/testbot/followers"


def test_build_actor_public_key_id():
    from app.activitypub.actor import build_actor

    assert build_actor().public_key.id == "https://bot.test/users/testbot#main-key"


def test_build_actor_public_key_owner():
    from app.activitypub.actor import build_actor

    assert build_actor().public_key.owner == "https://bot.test/users/testbot"


def test_build_actor_public_key_pem_is_not_empty():
    from app.activitypub.actor import build_actor

    assert "BEGIN PUBLIC KEY" in build_actor().public_key.public_key_pem


def test_build_actor_display_name():
    from app.activitypub.actor import build_actor

    assert build_actor().name == "Test Bot"


def test_load_private_key_returns_rsa_key():
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
    from app.activitypub.keys import load_private_key

    assert isinstance(load_private_key(), RSAPrivateKey)


def test_load_public_key_pem_returns_string():
    from app.activitypub.keys import load_public_key_pem

    pem = load_public_key_pem()
    assert isinstance(pem, str)
    assert pem.startswith("-----BEGIN PUBLIC KEY-----")


@pytest.mark.asyncio
async def test_get_keys_for_actor_returns_key_for_bot_username():
    from apkit.server.types import ActorKey
    from app.activitypub.keys import get_keys_for_actor

    keys = await get_keys_for_actor("testbot")
    assert len(keys) == 1
    assert isinstance(keys[0], ActorKey)
    assert keys[0].key_id == "https://bot.test/users/testbot#main-key"


@pytest.mark.asyncio
async def test_get_keys_for_actor_returns_empty_for_unknown_identifier():
    from app.activitypub.keys import get_keys_for_actor

    assert await get_keys_for_actor("outrobot") == []


@pytest.mark.asyncio
async def test_get_keys_for_actor_key_id_format():
    from app.activitypub.keys import get_keys_for_actor

    keys = await get_keys_for_actor("testbot")
    assert "#main-key" in keys[0].key_id
