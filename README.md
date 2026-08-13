# 🌐 translate-bot

Bot para o [Fediverso](https://pt.wikipedia.org/wiki/Fediverse) que traduz posts automaticamente quando mencionado.

Mencione `@translatebot@seu-dominio.com` em qualquer post e ele responde com o conteúdo traduzido para o idioma configurado.

```
@fulano@mastodon.social
Bonjour tout le monde, comment ça va ?

@translatebot@seu-dominio.com
🌐 [FR → PT] Olá a todos, como vão vocês?
```

Testado e funcionando com [Mastodon](https://joinmastodon.org/) e instâncias compatíveis com ActivityPub.

A cada release, publicamos uma imagem Docker pronta — veja [Deploy com Docker](#deploy-com-docker) pra subir sua própria instância sem precisar clonar o repositório.

---

## Tecnologias

| | |
|---|---|
| **[apkit](https://github.com/fedi-libs/apkit)** | Toolkit ActivityPub para Python — cuida de HTTP Signatures, WebFinger e NodeInfo |
| **[FastAPI](https://fastapi.tiangolo.com/)** | Servidor web assíncrono (vem como dependência do apkit) |
| **[LibreTranslate](https://libretranslate.com/)** | Detecção automática de idioma e tradução — open source, self-hostável |
| **[Dynaconf](https://www.dynaconf.com/)** | Configuração por ambiente com suporte a secrets |
| **[SQLAlchemy](https://www.sqlalchemy.org/) + SQLite** | Persistência leve de followers, notas de resposta, fila e deduplicação — sem dependências externas |
| **[uv](https://docs.astral.sh/uv/)** | Gerenciamento de dependências e ambiente virtual |

---

## Deploy com Docker

Duas formas de rodar o bot: usando a imagem já publicada (mais rápido — não precisa clonar o repositório nem instalar Python) ou buildando localmente (útil pra customizar o código).

### Opção 1 — imagem pronta (recomendado)

A cada release, uma imagem é publicada automaticamente em [`ghcr.io/riverfount/translate-bot`](https://github.com/Riverfount/translate-bot/pkgs/container/translate-bot).

**1. Gere as chaves RSA do bot** — não precisa de Python/uv local, usa a própria imagem:

```bash
mkdir -p keys
docker run --rm -v "$(pwd)/keys:/app/keys" ghcr.io/riverfount/translate-bot:latest uv run --no-sync gen-keys
```

Isso cria `keys/private.pem` e `keys/public.pem`. A chave privada assina as atividades enviadas pelo bot — **nunca a compartilhe**.

**2. Crie um banco vazio** — o bot cria as tabelas automaticamente no primeiro start:

```bash
touch bot.db
```

**3. Suba o container**, sobrescrevendo pelo menos o domínio via variável de ambiente:

```bash
docker run -d \
  --name translate-bot \
  -p 8000:8000 \
  -v "$(pwd)/keys:/app/keys" \
  -v "$(pwd)/bot.db:/app/bot.db" \
  -e ENV_FOR_DYNACONF=production \
  -e TRANSLATEBOT_DOMAIN=bot.seu-dominio.com \
  -e TRANSLATEBOT_BOT_USERNAME=translatebot \
  -e TRANSLATEBOT_TARGET_LANGUAGE=pt \
  -e TRANSLATEBOT_LIBRETRANSLATE_URL=https://sua-instancia-libretranslate.com \
  ghcr.io/riverfount/translate-bot:latest
```

Qualquer chave de `settings.toml` pode ser sobrescrita assim, com o prefixo `TRANSLATEBOT_` (veja [Configuração](#configuração)). Se a instância LibreTranslate exigir chave de API, monte um `.secrets.toml` também:

```bash
-v "$(pwd)/.secrets.toml:/app/.secrets.toml"
```

**4. Confira os logs e o healthcheck:**

```bash
docker logs -f translate-bot
docker ps   # STATUS deve mostrar "(healthy)" depois de uns 10s
```

Pra usar uma versão específica em vez de `latest`, troque a tag (ex: `ghcr.io/riverfount/translate-bot:v1.1.0`) — veja as [tags disponíveis](https://github.com/Riverfount/translate-bot/pkgs/container/translate-bot) e as [releases](https://github.com/Riverfount/translate-bot/releases).

> O container roda como usuário não-root e expõe `/health` pra orquestradores. Falta configurar HTTPS na frente — veja a seção [HTTPS](#https-obrigatório) logo abaixo, é obrigatório pro ActivityPub funcionar.

### Opção 2 — build local

Pra desenvolver ou customizar o código antes de buildar:

```bash
git clone https://github.com/Riverfount/translate-bot
cd translate-bot
make gen-keys
make docker-build
make docker-run
```

Para acompanhar os logs em tempo real:

```bash
make docker-logs
```

Para parar e remover o container:

```bash
make docker-stop
```

As variáveis `IMAGE_NAME`, `IMAGE_TAG` e `PORT` podem ser sobrescritas:

```bash
make docker-build IMAGE_NAME=meu-bot IMAGE_TAG=v1.0
make docker-run PORT=9000
```

---

## HTTPS (obrigatório)

O protocolo ActivityPub exige HTTPS. Servidores Mastodon rejeitam conexões sem TLS.

A forma mais simples com [Caddy](https://caddyserver.com/):

```
# Caddyfile
bot.seu-dominio.com {
    reverse_proxy localhost:8000
}
```

```bash
caddy run
```

O Caddy obtém e renova o certificado Let's Encrypt automaticamente.

---

## Pré-requisitos

Pra rodar a imagem pronta (veja [Deploy com Docker](#deploy-com-docker)):

- [Docker](https://docs.docker.com/get-docker/) (ou Podman)
- Um domínio com HTTPS apontando para o servidor (obrigatório para ActivityPub)
- Acesso a uma instância [LibreTranslate](https://libretranslate.com/) (pública ou self-hosted)

Pra desenvolver ou buildar a partir do código-fonte, além do acima:

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) instalado
- [make](https://www.gnu.org/software/make/) instalado (disponível na maioria dos sistemas Unix)

---

## Instalação

### 1. Instalar o uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clonar o repositório

```bash
git clone https://github.com/Riverfount/translate-bot
cd translate-bot
```

### 3. Instalar as dependências

```bash
make install-dev
```

O uv cria automaticamente o ambiente virtual em `.venv` e instala tudo a partir do `uv.lock`. Não é necessário ativar o venv manualmente.

### 4. Gerar as chaves RSA do bot

```bash
make gen-keys
```

Isso cria `keys/private.pem` e `keys/public.pem`. A chave privada é usada para assinar as atividades enviadas — **nunca a versione no git**.

### 5. Configurar o ambiente

Edite o `settings.toml` com o domínio do seu bot:

```toml
[production]
domain = "bot.seu-dominio.com"
```

Crie o arquivo `.secrets.toml` com a API key da instância LibreTranslate, se necessário (já está no `.gitignore`):

```toml
[default]
libretranslate_api_key = "sua-chave-aqui"
```

> Instâncias self-hosted sem autenticação podem deixar a chave em branco. A instância padrão `https://libretranslate.com` exige chave.

Para definir o ambiente ativo, crie um `.env` na raiz:

```
ENV_FOR_DYNACONF=production
```

### 6. Rodar o servidor

```bash
make run
```

Para desenvolvimento com hot-reload:

```bash
make dev
```

---

## Configuração

Todas as configurações ficam em `settings.toml`. Os segredos ficam separados em `.secrets.toml`.

```toml
# settings.toml

[default]
bot_username         = "translatebot"        # usuário do bot no Fediverso
bot_display_name     = "Translate Bot 🌐"
bot_summary          = "Mencione-me para traduzir qualquer post!"
target_language      = "pt"                  # idioma padrão de destino
libretranslate_url   = "https://libretranslate.com"  # instância LibreTranslate
libretranslate_api_key = ""                  # deixe em branco se não exigir chave
database_url         = "sqlite+aiosqlite:///./bot.db"
private_key_path     = "keys/private.pem"
public_key_path      = "keys/public.pem"
mention_cooldown_seconds = 30                # cooldown por autor entre respostas (anti-spam)
worker_concurrency   = 3                     # quantos workers processam a fila em paralelo

[development]
domain       = "localhost"
database_url = "sqlite+aiosqlite:///./bot_dev.db"

[production]
domain = "bot.seu-dominio.com"               # ← altere aqui
```

Qualquer configuração pode ser sobrescrita via variável de ambiente com o prefixo `TRANSLATEBOT_`:

```bash
TRANSLATEBOT_TARGET_LANGUAGE=en uv run uvicorn app.main:api --host 0.0.0.0 --port 8000
```

---

## Como funciona

```
Mastodon / Misskey / etc.                Translate Bot
        │                                      │
        │  POST /users/translatebot/inbox       │
        │  {type: "Create", object: Note} ─────▶│
        │                                      │
        │                        verifica HTTP Signature (apkit)
        │                        persiste a atividade e enfileira
        │                        retorna 202 Accepted imediatamente
        │                                      │
        │                        [workers em paralelo, background]
        │                        ignora se já processada (dedup)
        │                        ignora se a menção não tem tag Mention
        │                        ignora se o autor está em cooldown
        │                        extrai texto do post
        │                        detecta idioma de origem
        │                        traduz via LibreTranslate
        │                        monta Note de resposta
        │                        assina com draft-cavage e envia
        │                                      │
        │  ◀── resposta traduzida na thread ───│
```

O handler do inbox retorna `202` imediatamente — servidores Mastodon têm timeout curto. A tradução acontece em workers `asyncio` rodando em paralelo em background; se o processo cair com itens pendentes, eles são recuperados no próximo start.

---

## Estrutura do projeto

```
translate-bot/
├── app/
│   ├── main.py                   # Servidor ActivityPub + endpoints FastAPI
│   ├── config.py                 # Configurações via Dynaconf
│   ├── database.py               # Engine e sessão SQLAlchemy async
│   ├── activitypub/
│   │   ├── actor.py              # Perfil ActivityPub do bot
│   │   ├── keys.py               # Carregamento das chaves RSA
│   │   └── handlers.py           # Handlers de Follow, Undo e Create
│   ├── models/
│   │   ├── follower.py           # ORM model de followers
│   │   ├── note.py               # ORM model das notas de resposta enviadas
│   │   ├── queued_activity.py    # ORM model da fila persistida
│   │   ├── processed_activity.py # ORM model de deduplicação
│   │   └── mention_rate_limit.py # ORM model do cooldown por autor
│   └── services/
│       ├── translate.py          # Integração LibreTranslate
│       ├── queue.py              # Fila persistida (SQLite + asyncio.Queue)
│       ├── note_store.py         # Persistência das notas de resposta
│       ├── dedup.py              # Deduplicação de atividades processadas
│       └── rate_limit.py         # Cooldown por autor
├── workers/
│   └── inbox_worker.py           # Workers de tradução em paralelo (background)
├── scripts/
│   └── generate_keys.py          # Geração de chaves RSA
├── tests/                        # Suite de testes (pytest + asyncio)
├── .github/workflows/
│   ├── ci.yml                    # Lint, typecheck e testes em cada push/PR
│   └── release.yml               # Build + push da imagem e release em cada tag vX.Y.Z
├── keys/                         # Chaves RSA — git-ignored
├── settings.toml                 # Configurações (versionado)
├── .secrets.toml                 # Segredos — git-ignored
├── .env.example                  # Exemplo de variáveis de ambiente
├── Dockerfile                    # Imagem para deploy (usuário não-root + healthcheck)
├── .dockerignore                 # Exclui segredos e artefatos do contexto de build
├── Makefile                      # Comandos de gerenciamento do projeto
├── pyproject.toml                # Dependências e metadados
└── uv.lock                       # Lockfile — deve ser versionado
```

---

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

---

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

---

## Teste local com ngrok

Para testar sem um servidor público, use o [ngrok](https://ngrok.com/) para expor o servidor local:

```bash
# Terminal 1 — túnel ngrok
ngrok http 8000

# Terminal 2 — servidor
make dev
```

Atualize o `settings.toml` com a URL do ngrok na seção `[development]` e defina `ENV_FOR_DYNACONF=development` no `.env`.

---

## Notas

> **Releases são publicadas automaticamente.** A cada tag `vX.Y.Z` empurrada pra `main`, o workflow [`release.yml`](.github/workflows/release.yml) roda a suíte completa, builda e publica a imagem em `ghcr.io/riverfount/translate-bot` e cria a [release](https://github.com/Riverfount/translate-bot/releases) no GitHub com changelog gerado automaticamente a partir dos PRs mergeados.

> **apkit ainda não é estável.** A versão está fixada no `pyproject.toml`. Antes de atualizar, leia o [CHANGELOG](https://github.com/fedi-libs/apkit/blob/main/CHANGELOG.md) do projeto.

> **LibreTranslate é open source e self-hostável.** Para maior controle e sem custos por caractere, considere rodar sua própria instância. Instruções em [libretranslate.com](https://libretranslate.com/). O limite de 500 caracteres por requisição é configurável no código.

> **`uv.lock` deve ser versionado no git.** Ele garante que produção use exatamente as mesmas versões que desenvolvimento.

---

## Autor

Vicente Marçal — [@riverfount@bolha.us](https://bolha.us/@riverfount)

---

## Licença

MIT
