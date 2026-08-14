# translate-bot

Bot para o [Fediverso](https://pt.wikipedia.org/wiki/Fediverse) que traduz posts automaticamente quando mencionado.

Mencione `@translatebot@seu-dominio.com` em qualquer post e ele responde com o conteúdo traduzido para o idioma configurado.

```
@fulano@mastodon.social
Bonjour tout le monde, comment ça va ? @translatebot@seu-dominio.com

@translatebot@seu-dominio.com
🌐 [FR → PT] Olá a todos, como vão vocês?
```

Testado e funcionando com [Mastodon](https://joinmastodon.org/) e instâncias compatíveis com ActivityPub.

!!! tip "Comece rápido"
    A cada release publicamos uma imagem Docker pronta — veja
    [Deploy com Docker](deploy-docker.md) pra subir sua própria instância sem
    precisar clonar o repositório.

## Tecnologias

| | |
|---|---|
| **[apkit](https://github.com/fedi-libs/apkit)** | Toolkit ActivityPub para Python — cuida de HTTP Signatures, WebFinger e NodeInfo |
| **[FastAPI](https://fastapi.tiangolo.com/)** | Servidor web assíncrono (vem como dependência do apkit) |
| **[LibreTranslate](https://libretranslate.com/)** | Detecção automática de idioma e tradução — open source, self-hostável |
| **[Dynaconf](https://www.dynaconf.com/)** | Configuração por ambiente com suporte a secrets |
| **[SQLAlchemy](https://www.sqlalchemy.org/) + SQLite** | Persistência leve de followers, notas de resposta, fila e deduplicação — sem dependências externas |
| **[uv](https://docs.astral.sh/uv/)** | Gerenciamento de dependências e ambiente virtual |

## Próximos passos

- [Instalação](instalacao.md) — rodar o bot a partir do código-fonte
- [Configuração](configuracao.md) — `settings.toml`, secrets e variáveis de ambiente
- [Deploy com Docker](deploy-docker.md) — imagem pronta, build local e HTTPS
- [Arquitetura](arquitetura.md) — como o bot processa uma menção
- [Desenvolvimento](desenvolvimento.md) — testes e comandos úteis

## Contribuindo

Quer contribuir? Veja o [guia de contribuição](https://github.com/Riverfount/translate-bot/blob/main/CONTRIBUTING.md)
no repositório.

## Autor

Vicente Marçal — [@riverfount@bolha.us](https://bolha.us/@riverfount)

## Licença

MIT
