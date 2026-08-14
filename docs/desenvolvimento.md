# Desenvolvimento

## Testes

```bash
# Rodar todos os testes (cobertura incluída automaticamente)
make test

# Modo verbose
make test-v

# Apenas um módulo
make test-file FILE=tests/test_handlers.py

# Sem relatório de cobertura (mais rápido)
make test-fast
```

A cobertura é configurada automaticamente via `pyproject.toml` (branch coverage). A suite cobre translate, inbox_worker, handlers, actor/keys, persistência (followers, notas, fila, deduplicação, rate limit) e os endpoints principais do servidor.

## Comandos úteis

```bash
# Listar todos os comandos disponíveis
make help

# Verificar o código com o linter
make lint

# Corrigir erros de lint automaticamente
make lint-fix

# Formatar o código
make format

# Verificar tipos com mypy
make typecheck

# Formatar + lint + typecheck de uma vez
make check

# Remover artefatos gerados (cache, cobertura, build)
make clean

# Adicionar uma dependência
uv add nome-do-pacote

# Adicionar dependência só de desenvolvimento
uv add --group dev nome-do-pacote

# Atualizar apenas o apkit
uv lock --upgrade-package apkit
```

## Documentação

Este site é gerado com [MkDocs](https://www.mkdocs.org/) + [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/), a partir dos arquivos em `docs/`.

```bash
# Servir localmente com hot-reload
make docs-serve

# Gerar o site estático em site/
make docs-build
```

Um workflow (`.github/workflows/docs.yml`) publica o site automaticamente no GitHub Pages a cada push na `main` que altere `docs/` ou `mkdocs.yml`.

## Notas

!!! info "Releases são publicadas automaticamente"
    A cada tag `vX.Y.Z` empurrada pra `main`, o workflow [`release.yml`](https://github.com/Riverfount/translate-bot/blob/main/.github/workflows/release.yml) roda a suíte completa, builda e publica a imagem em `ghcr.io/riverfount/translate-bot` e cria a [release](https://github.com/Riverfount/translate-bot/releases) no GitHub com changelog gerado automaticamente a partir dos PRs mergeados.

!!! warning "apkit ainda não é estável"
    A versão está fixada no `pyproject.toml`. Antes de atualizar, leia o [CHANGELOG](https://github.com/fedi-libs/apkit/blob/main/CHANGELOG.md) do projeto.

!!! tip "LibreTranslate é open source e self-hostável"
    Para maior controle e sem custos por caractere, considere rodar sua própria instância. Instruções em [libretranslate.com](https://libretranslate.com/). O limite de 500 caracteres por requisição é configurável no código.

!!! note "`uv.lock` deve ser versionado no git"
    Ele garante que produção use exatamente as mesmas versões que desenvolvimento.
