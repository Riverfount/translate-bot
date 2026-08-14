# Configuração

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

## Overrides via variável de ambiente

Qualquer configuração pode ser sobrescrita via variável de ambiente com o prefixo `TRANSLATEBOT_`:

```bash
TRANSLATEBOT_TARGET_LANGUAGE=en uv run uvicorn app.main:api --host 0.0.0.0 --port 8000
```

Isso vale tanto para execução local quanto para containers Docker (veja
[Deploy com Docker](deploy-docker.md)).
