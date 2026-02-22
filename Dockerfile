FROM python:3.14-slim

# Instala o uv diretamente da imagem oficial Astral
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

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

# uv run ativa o venv automaticamente — não precisa de source .venv/bin/activate
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]