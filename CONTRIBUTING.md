# Contribuindo com o translate-bot

Obrigado pelo interesse em contribuir! Este documento descreve o processo para
reportar bugs, propor melhorias e enviar pull requests.

---

## Código de Conduta

Ao participar deste projeto, você concorda em seguir o nosso
[Código de Conduta](CODE_OF_CONDUCT.md). Por favor, leia-o antes de contribuir.

---

## Como reportar um bug

1. Verifique se o bug já foi reportado nas [Issues abertas](../../issues).
2. Se não encontrar, abra uma nova issue usando o template **Bug Report**.
3. Inclua o máximo de contexto possível: versão do Python, sistema operacional,
   logs de erro e passos para reproduzir.

---

## Como propor uma melhoria

1. Verifique se já existe uma issue ou discussão sobre a sua ideia.
2. Abra uma issue usando o template **Feature Request** descrevendo o problema
   que a melhoria resolve e como você imagina a solução.
3. Aguarde feedback antes de começar a implementar — isso evita trabalho em vão.

---

## Fluxo de trabalho para pull requests

### 1. Fork e clone

```bash
git clone https://github.com/<seu-usuario>/translate-bot
cd translate-bot
```

### 2. Configure o ambiente

```bash
# Instale o uv se ainda não tiver
curl -LsSf https://astral.sh/uv/install.sh | sh

# Instale as dependências (incluindo as de desenvolvimento)
uv sync
```

### 3. Crie um branch

Use um nome descritivo baseado na issue correspondente:

```bash
git checkout -b issue-42
# ou
git checkout -b fix/descricao-curta
git checkout -b feat/descricao-curta
```

### 4. Faça as alterações

- Escreva código limpo e consistente com o estilo existente.
- Adicione ou atualize testes para cobrir o que foi alterado.
- Mantenha os commits atômicos e com mensagens claras.

### 5. Verifique antes de enviar

```bash
# Lint
uv run ruff check .

# Formatação
uv run ruff format .

# Testes com cobertura
uv run pytest
```

Todos os checks devem passar antes de abrir o PR.

### 6. Abra o Pull Request

- Preencha o template do PR completamente.
- Referencie a issue relacionada (ex.: `Closes #42`).
- Aguarde a revisão — pode haver pedidos de ajustes.

---

## Padrões de código

| Ferramenta | Uso |
|---|---|
| **ruff** | Lint e formatação (substitui flake8, isort, black) |
| **pytest** | Testes unitários e de integração |
| **anyio** | Testes assíncronos |

A configuração do ruff e do pytest está em `pyproject.toml`.

---

## Estrutura de testes

Os testes ficam em `tests/`. Para adicionar testes:

```bash
tests/
├── test_handlers.py      # handlers ActivityPub
├── test_translate.py     # serviço de tradução
├── test_actor.py         # perfil do bot
└── ...
```

Use `pytest-anyio` para funções `async`. Veja os testes existentes como referência.

---

## Commits

Siga o padrão [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: adiciona suporte a idioma japonês
fix: corrige timeout na fila assíncrona
docs: atualiza README com exemplo de deploy
test: adiciona cobertura para handler de Undo
refactor: extrai lógica de detecção de idioma
```

---

## Dúvidas?

Abra uma issue ou entre em contato com o mantenedor:
**Vicente Marçal — [@riverfount@bolha.us](https://bolha.us/@riverfount)**
