# Arquitetura

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
│   ├── docs.yml                  # Build + publicação do site de documentação
│   └── release.yml               # Build + push da imagem e release em cada tag vX.Y.Z
├── docs/                          # Fonte do site de documentação (MkDocs)
├── keys/                         # Chaves RSA — git-ignored
├── settings.toml                 # Configurações (versionado)
├── .secrets.toml                 # Segredos — git-ignored
├── .env.example                  # Exemplo de variáveis de ambiente
├── Dockerfile                    # Imagem para deploy (usuário não-root + healthcheck)
├── .dockerignore                 # Exclui segredos e artefatos do contexto de build
├── Makefile                      # Comandos de gerenciamento do projeto
├── mkdocs.yml                    # Configuração do site de documentação
├── pyproject.toml                # Dependências e metadados
└── uv.lock                       # Lockfile — deve ser versionado
```
