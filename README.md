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

## 📚 Documentação completa

**https://riverfount.github.io/translate-bot/**

- [Instalação](https://riverfount.github.io/translate-bot/instalacao/) — rodar o bot a partir do código-fonte
- [Configuração](https://riverfount.github.io/translate-bot/configuracao/) — `settings.toml`, secrets e variáveis de ambiente
- [Deploy com Docker](https://riverfount.github.io/translate-bot/deploy-docker/) — imagem pronta, build local e HTTPS
- [Arquitetura](https://riverfount.github.io/translate-bot/arquitetura/) — como o bot processa uma menção
- [Desenvolvimento](https://riverfount.github.io/translate-bot/desenvolvimento/) — testes e comandos úteis

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

## Quickstart com Docker

```bash
mkdir -p keys
docker run --rm -v "$(pwd)/keys:/app/keys" ghcr.io/riverfount/translate-bot:latest uv run --no-sync gen-keys
touch bot.db
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

Passo a passo completo, pré-requisitos e configuração de HTTPS (obrigatório pro ActivityPub) em [Deploy com Docker](https://riverfount.github.io/translate-bot/deploy-docker/).

---

## Notas

> **Releases são publicadas automaticamente.** A cada tag `vX.Y.Z` empurrada pra `main`, o workflow [`release.yml`](.github/workflows/release.yml) roda a suíte completa, builda e publica a imagem em `ghcr.io/riverfount/translate-bot` e cria a [release](https://github.com/Riverfount/translate-bot/releases) no GitHub com changelog gerado automaticamente a partir dos PRs mergeados.

> **apkit ainda não é estável.** A versão está fixada no `pyproject.toml`. Antes de atualizar, leia o [CHANGELOG](https://github.com/fedi-libs/apkit/blob/main/CHANGELOG.md) do projeto.

> **LibreTranslate é open source e self-hostável.** Para maior controle e sem custos por caractere, considere rodar sua própria instância. Instruções em [libretranslate.com](https://libretranslate.com/).

---

## Contribuindo

Veja o [guia de contribuição](CONTRIBUTING.md) e o [código de conduta](CODE_OF_CONDUCT.md).

---

## Autor

Vicente Marçal — [@riverfount@bolha.us](https://bolha.us/@riverfount)

---

## Licença

MIT
