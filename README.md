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

---

## Tecnologias

| | |
|---|---|
| **[apkit](https://github.com/fedi-libs/apkit)** | Toolkit ActivityPub para Python — cuida de HTTP Signatures, WebFinger e NodeInfo |
| **[FastAPI](https://fastapi.tiangolo.com/)** | Servidor web assíncrono (vem como dependência do apkit) |
| **[Google Translate API](https://cloud.google.com/translate)** | Detecção automática de idioma e tradução |
| **[Dynaconf](https://www.dynaconf.com/)** | Configuração por ambiente com suporte a secrets |
| **[SQLAlchemy](https://www.sqlalchemy.org/) + SQLite** | Persistência leve de followers, sem dependências externas |
| **[uv](https://docs.astral.sh/uv/)** | Gerenciamento de dependências e ambiente virtual |

---

## Pré-requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) instalado
- Uma chave de API do [Google Cloud Translation](https://cloud.google.com/translate/docs/setup)
- Um domínio com HTTPS apontando para o servidor (obrigatório para ActivityPub)

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
uv sync
```

O uv cria automaticamente o ambiente virtual em `.venv` e instala tudo a partir do `uv.lock`. Não é necessário ativar o venv manualmente.

### 4. Gerar as chaves RSA do bot

```bash
uv run python scripts/generate_keys.py
```

Isso cria `keys/private.pem` e `keys/public.pem`. A chave privada é usada para assinar as atividades enviadas — **nunca a versione no git**.

### 5. Configurar o ambiente

Edite o `settings.toml` com o domínio do seu bot:

```toml
[production]
domain = "bot.seu-dominio.com"
```

Crie o arquivo `.secrets.toml` com sua API key (já está no `.gitignore`):

```toml
[default]
google_translate_api_key = "AIza..."
```

Para definir o ambiente ativo, crie um `.env` na raiz:

```
ENV_FOR_DYNACONF=production
```

### 6. Rodar o servidor

```bash
uv run uvicorn app.main:api --host 0.0.0.0 --port 8000
```

Para desenvolvimento com hot-reload:

```bash
uv run uvicorn app.main:api --host 0.0.0.0 --port 8000 --reload
```

---

## Configuração

Todas as configurações ficam em `settings.toml`. Os segredos ficam separados em `.secrets.toml`.

```toml
# settings.toml

[default]
bot_username      = "translatebot"        # usuário do bot no Fediverso
bot_display_name  = "Translate Bot 🌐"
bot_summary       = "Mencione-me para traduzir qualquer post!"
target_language   = "pt"                  # idioma padrão de destino
database_url      = "sqlite+aiosqlite:///./bot.db"
private_key_path  = "keys/private.pem"
public_key_path   = "keys/public.pem"

[development]
domain       = "localhost"
database_url = "sqlite+aiosqlite:///./bot_dev.db"

[production]
domain = "bot.seu-dominio.com"            # ← altere aqui
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
        │                        enfileira na fila assíncrona
        │                        retorna 202 Accepted imediatamente
        │                                      │
        │                        [worker em background]
        │                        extrai texto do post
        │                        detecta idioma de origem
        │                        traduz via Google Translate
        │                        monta Note de resposta
        │                        assina com draft-cavage e envia
        │                                      │
        │  ◀── resposta traduzida na thread ───│
```

O handler do inbox retorna `202` imediatamente — servidores Mastodon têm timeout curto. A tradução acontece em um worker `asyncio` em background.

---

## Estrutura do projeto

```
translate-bot/
├── app/
│   ├── main.py                  # Servidor ActivityPub + endpoints FastAPI
│   ├── config.py                # Configurações via Dynaconf
│   ├── database.py              # Engine e sessão SQLAlchemy async
│   ├── activitypub/
│   │   ├── actor.py             # Perfil ActivityPub do bot
│   │   ├── keys.py              # Carregamento das chaves RSA
│   │   └── handlers.py          # Handlers de Follow e Create
│   ├── models/
│   │   └── follower.py          # ORM model de followers
│   └── services/
│       ├── translate.py         # Integração Google Translate
│       └── queue.py             # Fila assíncrona asyncio
├── workers/
│   └── inbox_worker.py          # Worker de tradução em background
├── scripts/
│   └── generate_keys.py         # Geração de chaves RSA
├── tests/                       # Suite de testes (pytest + anyio)
├── keys/                        # Chaves RSA — git-ignored
├── settings.toml                # Configurações (versionado)
├── .secrets.toml                # Segredos — git-ignored
├── .env.example                 # Exemplo de variáveis de ambiente
├── Dockerfile                   # Imagem para deploy
├── pyproject.toml               # Dependências e metadados
└── uv.lock                      # Lockfile — deve ser versionado
```

---

## Testes

```bash
# Rodar todos os testes
uv run pytest

# Com cobertura
uv run pytest --cov=app --cov=workers

# Apenas um módulo
uv run pytest tests/test_handlers.py -v
```

A suite cobre translate, inbox_worker, handlers, actor/keys e os endpoints principais do servidor.

---

## Comandos úteis

```bash
# Verificar o código com o linter
uv run ruff check .

# Formatar o código
uv run ruff format .

# Adicionar uma dependência
uv add nome-do-pacote

# Adicionar dependência só de desenvolvimento
uv add --group dev nome-do-pacote

# Atualizar apenas o apkit
uv lock --upgrade-package apkit
```

---

## Deploy com Docker

```bash
docker build -t translate-bot .
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/keys:/app/keys \
  -v $(pwd)/bot.db:/app/bot.db \
  -e ENV_FOR_DYNACONF=production \
  -e TRANSLATEBOT_GOOGLE_TRANSLATE_API_KEY=AIza... \
  translate-bot
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

## Teste local com ngrok

Para testar sem um servidor público, use o [ngrok](https://ngrok.com/) para expor o servidor local:

```bash
# Terminal 1 — túnel ngrok
ngrok http 8000

# Terminal 2 — servidor
uv run uvicorn app.main:api --host 0.0.0.0 --port 8000 --reload
```

Atualize o `settings.toml` com a URL do ngrok na seção `[development]` e defina `ENV_FOR_DYNACONF=development` no `.env`.

---

## Notas

> **apkit ainda não é estável.** A versão está fixada no `pyproject.toml`. Antes de atualizar, leia o [CHANGELOG](https://github.com/fedi-libs/apkit/blob/main/CHANGELOG.md) do projeto.

> **Google Translate cobra por caractere.** Para bots com alto volume, considere adicionar rate limiting por remetente no handler de `Create`. O plano gratuito oferece 500.000 caracteres/mês.

> **`uv.lock` deve ser versionado no git.** Ele garante que produção use exatamente as mesmas versões que desenvolvimento.

---

## Autor

Vicente Marçal — [@riverfount@bolha.us](https://bolha.us/@riverfount)

---

## Licença

MIT