"""
app/database.py

Configuração do banco de dados SQLite via SQLAlchemy assíncrono.

Exporta:
- `engine`               — engine assíncrona compartilhada
- `async_session_factory` — fábrica de sessões para uso nos repositórios
- `Base`                 — classe base para os modelos ORM
- `get_session()`        — dependência FastAPI que fornece sessão por request
- `init_db()`            — cria as tabelas na inicialização da aplicação
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)

# ---------------------------------------------------------------------------
# Fábrica de sessões
# ---------------------------------------------------------------------------

# Nome distinto de AsyncSession (classe) para evitar colisão no mesmo módulo
async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,  # evita lazy-load após commit em contexto assíncrono
    class_=AsyncSession,
)


# ---------------------------------------------------------------------------
# Base declarativa
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Dependência FastAPI
# ---------------------------------------------------------------------------

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependência FastAPI que fornece uma sessão de banco por request.
    Faz commit automático em caso de sucesso e rollback em caso de exceção.
    """
    async with async_session_factory() as session:
        async with session.begin():
            yield session


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """
    Cria todas as tabelas definidas nos modelos ORM caso ainda não existam.
    Deve ser chamado uma única vez no startup da aplicação (lifespan do FastAPI).
    """
    # Importa os modelos para que o SQLAlchemy os registre no metadata da Base
    # antes de criar as tabelas. Sem este import, as tabelas não serão criadas.
    from app.models import follower  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
