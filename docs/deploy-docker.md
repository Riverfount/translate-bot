# Deploy com Docker

Duas formas de rodar o bot: usando a imagem já publicada (mais rápido — não precisa clonar o repositório nem instalar Python) ou buildando localmente (útil pra customizar o código).

## Opção 1 — imagem pronta (recomendado)

A cada release, uma imagem é publicada automaticamente em [`ghcr.io/riverfount/translate-bot`](https://github.com/Riverfount/translate-bot/pkgs/container/translate-bot).

### 1. Gere as chaves RSA do bot

Não precisa de Python/uv local, usa a própria imagem:

```bash
mkdir -p keys
docker run --rm -v "$(pwd)/keys:/app/keys" ghcr.io/riverfount/translate-bot:latest uv run --no-sync gen-keys
```

Isso cria `keys/private.pem` e `keys/public.pem`. A chave privada assina as atividades enviadas pelo bot — **nunca a compartilhe**.

### 2. Crie um banco vazio

O bot cria as tabelas automaticamente no primeiro start:

```bash
touch bot.db
```

### 3. Suba o container

Sobrescrevendo pelo menos o domínio via variável de ambiente:

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

Qualquer chave de `settings.toml` pode ser sobrescrita assim, com o prefixo `TRANSLATEBOT_` (veja [Configuração](configuracao.md)). Se a instância LibreTranslate exigir chave de API, monte um `.secrets.toml` também:

```bash
-v "$(pwd)/.secrets.toml:/app/.secrets.toml"
```

### 4. Confira os logs e o healthcheck

```bash
docker logs -f translate-bot
docker ps   # STATUS deve mostrar "(healthy)" depois de uns 10s
```

Pra usar uma versão específica em vez de `latest`, troque a tag (ex: `ghcr.io/riverfount/translate-bot:v1.1.0`) — veja as [tags disponíveis](https://github.com/Riverfount/translate-bot/pkgs/container/translate-bot) e as [releases](https://github.com/Riverfount/translate-bot/releases).

!!! note
    O container roda como usuário não-root e expõe `/health` pra orquestradores. Falta configurar HTTPS na frente — veja a seção [HTTPS](#https-obrigatorio) logo abaixo, é obrigatório pro ActivityPub funcionar.

## Opção 2 — build local

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
