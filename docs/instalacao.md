# Instalação

Passo a passo pra rodar o bot a partir do código-fonte. Se você só quer subir
uma instância sem mexer no código, veja [Deploy com Docker](deploy-docker.md).

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) (ou Podman)
- Um domínio com HTTPS apontando para o servidor (obrigatório para ActivityPub)
- Acesso a uma instância [LibreTranslate](https://libretranslate.com/) (pública ou self-hosted)

Pra desenvolver ou buildar a partir do código-fonte, além do acima:

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) instalado
- [make](https://www.gnu.org/software/make/) instalado (disponível na maioria dos sistemas Unix)

## 1. Instalar o uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 2. Clonar o repositório

```bash
git clone https://github.com/Riverfount/translate-bot
cd translate-bot
```

## 3. Instalar as dependências

```bash
make install-dev
```

O uv cria automaticamente o ambiente virtual em `.venv` e instala tudo a partir do `uv.lock`. Não é necessário ativar o venv manualmente.

## 4. Gerar as chaves RSA do bot

```bash
make gen-keys
```

Isso cria `keys/private.pem` e `keys/public.pem`. A chave privada é usada para assinar as atividades enviadas — **nunca a versione no git**.

## 5. Configurar o ambiente

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

!!! note
    Instâncias self-hosted sem autenticação podem deixar a chave em branco. A instância padrão `https://libretranslate.com` exige chave.

Para definir o ambiente ativo, crie um `.env` na raiz:

```
ENV_FOR_DYNACONF=production
```

Veja todas as opções em [Configuração](configuracao.md).

## 6. Rodar o servidor

```bash
make run
```

Para desenvolvimento com hot-reload:

```bash
make dev
```

## Teste local com ngrok

Para testar sem um servidor público, use o [ngrok](https://ngrok.com/) para expor o servidor local:

```bash
# Terminal 1 — túnel ngrok
ngrok http 8000

# Terminal 2 — servidor
make dev
```

Atualize o `settings.toml` com a URL do ngrok na seção `[development]` e defina `ENV_FOR_DYNACONF=development` no `.env`.
