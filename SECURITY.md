# Política de Segurança

## Versões suportadas

| Versão | Suportada |
|--------|-----------|
| `main` (última) | ✅ |
| branches antigas | ❌ |

Apenas a versão mais recente do branch `main` recebe correções de segurança.

---

## Reportando uma vulnerabilidade

**Não abra uma issue pública para reportar vulnerabilidades de segurança.**

Se você encontrou uma vulnerabilidade, por favor reporte de forma privada:

- **Fediverse (preferencial):** [@riverfount@bolha.us](https://bolha.us/@riverfount)
  — envie uma mensagem direta (DM)
- **GitHub:** use [Security Advisories](../../security/advisories/new) — opção
  "Report a vulnerability" no repositório (requer conta GitHub)

### O que incluir no relatório

Para agilizar a análise, inclua:

- Descrição da vulnerabilidade e qual componente afeta
- Passos para reproduzir ou prova de conceito (PoC)
- Impacto potencial (confidencialidade, integridade, disponibilidade)
- Versão ou commit onde foi encontrada
- Sugestão de correção, se tiver

---

## Processo de resposta

1. **Confirmação:** você receberá uma confirmação de recebimento em até **72 horas**.
2. **Avaliação:** o mantenedor avaliará a severidade e o impacto.
3. **Correção:** uma correção será desenvolvida e testada de forma privada.
4. **Divulgação:** após a correção ser publicada, um Security Advisory será aberto
   descrevendo a vulnerabilidade. O crédito ao relator será incluído, salvo se
   preferir anonimato.

---

## Escopo

Este projeto é um bot ActivityPub que processa mensagens do Fediverso e realiza
chamadas à API do LibreTranslate. As principais superfícies de ataque incluem:

- **Inbox ActivityPub:** validação de HTTP Signatures e payloads JSON-LD
- **Integração LibreTranslate:** vazamento de API key ou SSRF
- **Banco de dados SQLite:** injeção via ORM (SQLAlchemy)
- **Chaves RSA:** armazenamento e carregamento das chaves privadas

---

## Fora do escopo

- Vulnerabilidades em dependências externas (reporte diretamente ao projeto
  correspondente: apkit, FastAPI, LibreTranslate, etc.)
- Instâncias self-hosted configuradas de forma insegura pelo operador
- Ataques que exigem acesso físico ao servidor

---

## Agradecimentos

Agradecemos a todos que reportam vulnerabilidades de forma responsável. Sua
contribuição ajuda a manter o projeto seguro para toda a comunidade.
