# Extração de NF com LLM

Projeto de estudos (PDI) para extração de dados de **Nota Fiscal** utilizando **LangChain** e **LLM**.

## Documentação

| Documento | Descrição |
|-----------|-----------|
| [Técnicas de Prompting](docs/tecnica-de-prompting.md) | One-shot, Few-shot e Chain of Thought aplicados à extração de NF |

## Pré-requisitos

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
cp .env.example .env
make install
make run
```

O servidor sobe em `http://0.0.0.0:8000`. Health check: `GET /health`.

## Comandos úteis

| Comando | Descrição |
|---------|-----------|
| `make install` | Instala dependências com uv |
| `make run` | Sobe o servidor com hot reload |
| `make lint` | Ruff + mypy |
| `make format` | Formata o código |
| `make test` | Roda os testes com coverage |

## Status

Em desenvolvimento incremental.

**Implementado:**
- API FastAPI com configuração, logging e health check
- Contrato Pydantic da extração de NF (domínio)
- Endpoint `POST /extrair-nf` com validação de upload (stub, sem LLM)
- Preparação de documento para o LLM (validação + data URI base64)
- Prompt few-shot + chain LangChain com Gemini (`with_structured_output`)
- Serviço de orquestração extrator_nf (erros LLM + inconsistências)

**Pendente:**
- Integração final no endpoint, suíte de testes consolidada e observabilidade

