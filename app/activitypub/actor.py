from apkit.models import Person, CryptographicKey
from app.config import settings
from app.activitypub.keys import load_public_key_pem


def build_actor() -> Person:
    base     = f"https://{settings.domain}"
    actor_url = f"{base}/users/{settings.bot_username}"

    return Person(
        id=actor_url,
        name=settings.bot_display_name,
        preferredUsername=settings.bot_username,
        summary=settings.bot_summary,
        inbox=f"{actor_url}/inbox",
        outbox=f"{actor_url}/outbox",
        followers=f"{actor_url}/followers",
        publicKey=CryptographicKey(
            id=f"{actor_url}#main-key",
            owner=actor_url,
            publicKeyPem=load_public_key_pem(),
        ),
        manuallyApprovesFollowers=False,
    )