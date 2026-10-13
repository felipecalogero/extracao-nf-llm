# Extração de NF com LLM

Projeto de estudos (PDI) para extração de dados de **Nota Fiscal** utilizando **LangChain** e **LLM**.

## Documentação

| Documento | Descrição |
|-----------|-----------|
| [Técnicas de Prompting](docs/tecnica-de-prompting.md) | One-shot, Few-shot e Chain of Thought aplicados à extração de NF |
| [Teste real com Gemini](docs/teste-real.md) | Passos com `curl` para validar a API com chave real |

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
| `make docker-build` | Gera a imagem Docker |
| `make docker-run` | Sobe a imagem usando o `.env` |

## Observabilidade (LangSmith)

Opcional. No `.env`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=sua_chave
LANGSMITH_PROJECT=extracao-nf-llm
```

Cada chamada a `POST /extrair-nf` gera um trace `extrair_nota_fiscal` com o tipo e o tamanho do arquivo nos metadados.

## Docker

```bash
make docker-build
make docker-run
```

A imagem expõe a porta 8000 e tem `HEALTHCHECK` em `GET /health`.

## CI

O workflow `.github/workflows/ci.yml` roda ruff, mypy, pytest e o build da imagem Docker em pushes na `main` e em pull requests.

## Status

**Implementado:**
- API FastAPI com configuração, logging e health check
- Contrato Pydantic da extração de NF (domínio)
- Endpoint `POST /extrair-nf` integrado ao extrator, com validação de upload e mapeamento HTTP de erros
- Preparação de documento para o LLM (validação + data URI base64)
- Prompt few-shot + chain LangChain com Gemini (`with_structured_output`)
- Serviço de orquestração extrator_nf (erros LLM + inconsistências)
- Suíte de testes consolidada (`tests/conftest.py`, `tests/fakes.py`, unit + integration)
- Tracing LangSmith, Dockerfile com healthcheck e CI
