FROM python:3.14-slim

# Instala o uv diretamente da imagem oficial Astral
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Usuário não-root — evita rodar o processo da aplicação como root no
# container. UID/GID 1000 é a convenção mais comum pro primeiro usuário
# não-root em hosts Linux — se os arquivos montados via volume no runtime
# (keys/, bot.db — ver Makefile: docker-run) pertencerem a outro UID no
# host, ajuste a titularidade deles ou este UID/GID de acordo.
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --create-home --shell /bin/bash appuser

WORKDIR /app

# Copia apenas os arquivos de dependência primeiro — maximiza cache de camadas.
# Se apenas o código mudar (não as deps), esta camada não é reconstruída.
COPY pyproject.toml uv.lock ./

# Instala dependências de produção em /app/.venv sem instalar o projeto em si.
# --frozen garante que o uv.lock seja respeitado exatamente (sem resolver novamente).
RUN uv sync --frozen --no-install-project --no-group dev

# Copia o restante do código
COPY . .

# Instala o projeto no venv já existente
RUN uv sync --frozen --no-group dev

# /app precisa ser gravável pelo usuário não-root — é onde o SQLite cria/
# atualiza o banco quando não montado como volume (ex: ambiente de dev)
RUN chown -R appuser:appuser /app

USER appuser

# Usa python3 do sistema (não `uv run`) para não disparar sync de
# dependências a cada verificação — só depende da stdlib.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

# uv run ativa o venv automaticamente — não precisa de source .venv/bin/activate.
# --no-sync evita que `uv run` tente reconciliar/ressincronizar o ambiente
# (incluindo baixar o grupo dev — mypy, ruff, ...) a cada start do container:
# o venv já foi montado no build, então runtime não deve depender de rede.
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:api", "--host", "0.0.0.0", "--port", "8000"]
