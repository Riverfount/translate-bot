"""
app/models/follower.py

Modelo ORM para persistência de followers do bot.

Armazena o actor_url de cada conta que seguiu o bot,
permitindo entregar atividades futuras para os followers
(ex: posts públicos, se o bot vier a publicar).
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Follower(Base):
    __tablename__ = "followers"

    # URL canônica do actor remoto — identificador único no Fediverso
    # ex: "https://mastodon.social/users/fulano"
    actor_url: Mapped[str] = mapped_column(String(2048), primary_key=True)

    # Inbox do actor — cached para evitar re-fetch a cada entrega
    inbox_url: Mapped[str] = mapped_column(String(2048))

    # Data em que o Follow foi aceito
    # insert_default é avaliado pelo SQLAlchemy no momento do INSERT,
    # garantindo o timezone correto independente da configuração do sistema
    followed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        insert_default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Follower actor_url={self.actor_url!r}>"
