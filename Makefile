.DEFAULT_GOAL := help

# ─── variáveis ────────────────────────────────────────────────────────────────

IMAGE_NAME  ?= translate-bot
IMAGE_TAG   ?= latest
PORT        ?= 8000

# ─── ajuda ────────────────────────────────────────────────────────────────────

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── instalação ───────────────────────────────────────────────────────────────

.PHONY: install
install: ## Instala dependências de produção
	uv sync --no-group dev

.PHONY: install-dev
install-dev: ## Instala todas as dependências (incluindo dev)
	uv sync

# ─── chaves RSA ───────────────────────────────────────────────────────────────

.PHONY: gen-keys
gen-keys: ## Gera o par de chaves RSA do bot em keys/
	uv run python scripts/generate_keys.py

# ─── desenvolvimento ──────────────────────────────────────────────────────────

.PHONY: run
run: ## Inicia o servidor (produção)
	uv run uvicorn app.main:api --host 0.0.0.0 --port $(PORT)

.PHONY: dev
dev: ## Inicia o servidor com hot-reload (desenvolvimento)
	uv run uvicorn app.main:api --host 0.0.0.0 --port $(PORT) --reload

# ─── qualidade de código ──────────────────────────────────────────────────────

.PHONY: lint
lint: ## Verifica o código com ruff
	uv run ruff check .

.PHONY: lint-fix
lint-fix: ## Corrige automaticamente os erros detectados pelo ruff
	uv run ruff check . --fix

.PHONY: format
format: ## Formata o código com ruff
	uv run ruff format .

.PHONY: format-check
format-check: ## Verifica formatação sem alterar arquivos
	uv run ruff format . --check

.PHONY: typecheck
typecheck: ## Verifica tipos com mypy
	uv run mypy app workers

.PHONY: check
check: format lint typecheck ## Executa format, lint e typecheck em sequência

# ─── testes ───────────────────────────────────────────────────────────────────

.PHONY: test
test: ## Executa a suite de testes com cobertura
	uv run pytest

.PHONY: test-v
test-v: ## Executa os testes em modo verbose
	uv run pytest -v

.PHONY: test-fast
test-fast: ## Executa os testes sem relatório de cobertura
	uv run pytest --no-cov

.PHONY: test-file
test-file: ## Executa um arquivo de teste específico  (uso: make test-file FILE=tests/test_handlers.py)
	uv run pytest $(FILE) -v

# ─── docker ───────────────────────────────────────────────────────────────────

.PHONY: docker-build
docker-build: ## Constrói a imagem Docker
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

.PHONY: docker-run
docker-run: ## Inicia o container (requer keys/ e .secrets.toml)
	docker run -d \
		--name $(IMAGE_NAME) \
		-p $(PORT):8000 \
		-v $$(pwd)/keys:/app/keys \
		-v $$(pwd)/bot.db:/app/bot.db \
		-e ENV_FOR_DYNACONF=production \
		$(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: docker-stop
docker-stop: ## Para e remove o container
	docker stop $(IMAGE_NAME) && docker rm $(IMAGE_NAME)

.PHONY: docker-logs
docker-logs: ## Exibe os logs do container em tempo real
	docker logs -f $(IMAGE_NAME)

# ─── limpeza ──────────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove artefatos gerados (cache, build, cobertura)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .mypy_cache  -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .ruff_cache  -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null; true
	rm -rf htmlcov .coverage coverage.xml 2>/dev/null; true

.PHONY: clean-db
clean-db: ## Remove os bancos de dados de desenvolvimento e teste
	rm -f bot_dev.db bot_test.db
