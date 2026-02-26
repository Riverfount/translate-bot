"""
Fixtures compartilhadas entre todos os testes.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


# ---------------------------------------------------------------------------
# Chaves RSA geradas em memória — evita dependência de arquivos em disco
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def rsa_private_key():
    """Par de chaves RSA gerado uma única vez por sessão de testes."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def rsa_private_key_pem(rsa_private_key) -> bytes:
    return rsa_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


@pytest.fixture(scope="session")
def rsa_public_key_pem(rsa_private_key) -> str:
    return (
        rsa_private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )


# ---------------------------------------------------------------------------
# Configuração Dynaconf isolada para testes
# Usa monkeypatch para sobrescrever os atributos sem tocar em arquivos .toml
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch, rsa_private_key_pem, rsa_public_key_pem, tmp_path):
    """
    Sobrescreve as settings do Dynaconf com valores de teste.
    `autouse=True` garante que nenhum teste acesse configurações reais
    ou tente ler arquivos de chave do disco.
    """
    from app import config

    # Escreve as chaves em arquivos temporários para os módulos que usam open()
    private_pem_path = tmp_path / "private.pem"
    public_pem_path = tmp_path / "public.pem"
    private_pem_path.write_bytes(rsa_private_key_pem)
    public_pem_path.write_text(rsa_public_key_pem)

    monkeypatch.setattr(config.settings, "domain", "bot.test")
    monkeypatch.setattr(config.settings, "bot_username", "testbot")
    monkeypatch.setattr(config.settings, "bot_display_name", "Test Bot")
    monkeypatch.setattr(config.settings, "bot_summary", "Bot de teste")
    monkeypatch.setattr(config.settings, "target_language", "pt")
    monkeypatch.setattr(config.settings, "google_translate_api_key", "fake-api-key")
    monkeypatch.setattr(config.settings, "private_key_path", str(private_pem_path))
    monkeypatch.setattr(config.settings, "public_key_path", str(public_pem_path))


# ---------------------------------------------------------------------------
# Factories de objetos apkit para uso nos testes
# ---------------------------------------------------------------------------


@pytest.fixture
def remote_actor_url() -> str:
    return "https://mastodon.social/users/fulano"


@pytest.fixture
def bot_actor_url() -> str:
    return "https://bot.test/users/testbot"


@pytest.fixture
def make_note(bot_actor_url):
    """Factory que cria objetos Note do apkit com valores padrão."""
    from apkit.models import Note

    def _make(
        content: str = "<p>Mensagem de teste</p>",
        note_id: str = "https://mastodon.social/users/fulano/statuses/1",
        attributed_to: str = "https://mastodon.social/users/fulano",
    ) -> Note:
        return Note(
            id=note_id,
            attributed_to=attributed_to,
            content=content,
            to=["https://www.w3.org/ns/activitystreams#Public"],
            cc=[bot_actor_url],
        )

    return _make


@pytest.fixture
def make_create(remote_actor_url, make_note):
    """Factory que cria objetos Create do apkit."""
    from apkit.models import Create

    def _make(note=None, actor: str | None = None) -> Create:
        return Create(
            id="https://mastodon.social/users/fulano/statuses/1/activity",
            actor=actor or remote_actor_url,
            object=note or make_note(),
            to=["https://www.w3.org/ns/activitystreams#Public"],
        )

    return _make


@pytest.fixture
def make_follow(remote_actor_url, bot_actor_url):
    """Factory que cria objetos Follow do apkit."""
    from apkit.models import Follow

    def _make(follower: str | None = None) -> Follow:
        return Follow(
            id="https://mastodon.social/users/fulano#follows/1",
            actor=follower or remote_actor_url,
            object=bot_actor_url,
        )

    return _make


@pytest.fixture
def mock_ctx(make_create):
    """
    Mock do Context do apkit.
    ctx.send() é o ponto de saída de atividades — mockamos para evitar
    requisições HTTP reais nos testes do worker e dos handlers.
    """
    ctx = MagicMock()
    ctx.activity = make_create()
    ctx.send = AsyncMock()
    return ctx
