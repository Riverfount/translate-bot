from cryptography.hazmat.primitives import serialization
from apkit.server.types import ActorKey
from app.config import settings


def load_private_key():
    with open(settings.private_key_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_public_key_pem() -> str:
    with open(settings.public_key_path) as f:
        return f.read()


async def get_keys_for_actor(identifier: str) -> list[ActorKey]:
    """
    Callback exigido pelo apkit para assinar atividades de saída.
    Recebe o `identifier` (username na URL) e retorna a(s) chave(s) do actor.
    """
    if identifier == settings.bot_username:
        private_key = load_private_key()
        key_id = f"https://{settings.domain}/users/{settings.bot_username}#main-key"
        return [ActorKey(key_id=key_id, private_key=private_key)]
    return []


async def get_bot_keys() -> list[ActorKey]:
    """Retorna as chaves do bot. Atalho para uso nos handlers."""
    return await get_keys_for_actor(settings.bot_username)
