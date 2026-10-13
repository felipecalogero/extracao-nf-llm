# Teste real com Gemini

Chamada ponta a ponta do `POST /extrair-nf` com uma chave real do Google AI Studio.

## Pré-requisitos

1. Copie o exemplo de env e preencha a chave:

```bash
cp .env.example .env
# edite .env e defina GOOGLE_API_KEY=...
```

2. Suba a API:

```bash
make run
```

## Curl

Com um PDF (ou PNG/JPEG) local:

```bash
curl -sS -X POST "http://127.0.0.1:8000/extrair-nf" \
  -F "arquivo=@./caminho/para/nota.pdf;type=application/pdf" \
  | python -m json.tool
```

Imagem:

```bash
curl -sS -X POST "http://127.0.0.1:8000/extrair-nf" \
  -F "arquivo=@./caminho/para/nota.png;type=image/png" \
  | python -m json.tool
```

Resposta esperada: HTTP 200 com `nota_fiscal` e `inconsistencias` (lista, possivelmente vazia).
