# Técnicas de Prompting para LLMs

Documentação de referência para o projeto de estudos **Extração de Dados de Nota Fiscal (NF)** com LangChain e LLM — desenvolvido como parte do PDI (Plano de Desenvolvimento Individual).

O objetivo é explicar as principais técnicas de criação de prompts, quando aplicá-las e como elas se encaixam no fluxo de um serviço de extração de dados fiscais.

---

## Índice

1. [O que é um prompt?](#o-que-é-um-prompt)
2. [One-shot Prompting](#one-shot-prompting)
3. [Few-shot Prompting](#few-shot-prompting)
4. [Chain of Thought (CoT)](#chain-of-thought-cot)
5. [Comparativo rápido](#comparativo-rápido)

---

## O que é um prompt?

Um **prompt** é a instrução (texto, exemplos, contexto e formato de saída) enviada ao modelo de linguagem (LLM) para orientar sua resposta. Em um serviço de extração de NF, o prompt define:

- **O que** extrair (CNPJ, valor total, chave de acesso, itens, etc.)
- **Como** estruturar a resposta (JSON, campos obrigatórios, tipos)
- **Quais regras** seguir (validação de CNPJ, formato de data, tratamento de campos ausentes)

A escolha da técnica de prompting impacta **precisão**, **custo** (tokens), **latência** e **manutenibilidade** do sistema.

---

## One-shot Prompting

### Conceito e objetivo

**One-shot prompting** (ou *prompt com um exemplo*) consiste em fornecer **uma única demonstração** de entrada e saída esperada antes de pedir ao modelo que processe o caso real.

O objetivo é **ancorar o comportamento** do LLM: formato de resposta, nomenclatura dos campos, nível de detalhe e tratamento de ambiguidades — sem precisar de vários exemplos nem de raciocínio explícito passo a passo.

> **Relação com Zero-shot:** em *zero-shot*, não há exemplos; apenas instruções. O *one-shot* adiciona **um** par `(entrada → saída)` como referência.

### Como funciona

1. Você define a **tarefa** em linguagem natural (system/user message).
2. Inclui **um exemplo completo**: texto ou OCR da NF + JSON extraído corretamente.
3. Envia o **documento real** a ser processado.
4. O modelo generaliza a partir do padrão demonstrado no exemplo único.

No LangChain, isso costuma ser modelado como mensagens sequenciais ou variáveis em um `ChatPromptTemplate`:

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "Você extrai dados estruturados de Notas Fiscais eletrônicas (NF-e)."),
    ("human", "Exemplo:\n\nEntrada:\n{exemplo_entrada}\n\nSaída:\n{exemplo_saida}"),
    ("human", "Agora extraia os dados da NF abaixo:\n\n{nf_texto}"),
])
```

### Quando utilizar

| Cenário | Indicado? |
|---------|-----------|
| Formato de saída JSON bem definido e estável | Sim |
| Layout das NFs é relativamente padronizado (NF-e modelo 55) | Sim |
| Primeira versão do extrator (MVP) | Sim |
| NFs com layouts muito heterogêneos (DANFE de vários ERPs) | Com cautela — considere few-shot |
| Tarefa que exige validação cruzada complexa | Complemente com CoT |

### Vantagens e desvantagens

| Vantagens | Desvantagens |
|-----------|--------------|
| Simples de implementar e manter | Um único exemplo pode não cobrir variações de layout |
| Baixo consumo de tokens comparado ao few-shot | Se o exemplo for atípico, o modelo pode replicar o erro |
| Boa relação custo/benefício para formatos padronizados | Menos robusto que few-shot em casos extremos |
| Facilita onboarding de novos devs no time | Não expõe o raciocínio interno (difícil debugar erros lógicos) |

### Exemplo prático — extração de NF-e

**Entrada (trecho OCR da NF):**

```
NOTA FISCAL ELETRÔNICA - NF-e
Nº 000.123.456  Série 1  Emissão: 15/03/2026
Emitente: ACME LTDA  CNPJ: 12.345.678/0001-90
Destinatário: CLIENTE SA  CNPJ: 98.765.432/0001-10
Valor Total da NF: R$ 1.250,00
Chave de Acesso: 35260312345678000190550010001234561123456789
```

**Saída esperada (exemplo único no prompt):**

```json
{
  "numero": "123456",
  "serie": "1",
  "data_emissao": "2026-03-15",
  "emitente": {
    "razao_social": "ACME LTDA",
    "cnpj": "12345678000190"
  },
  "destinatario": {
    "razao_social": "CLIENTE SA",
    "cnpj": "98765432000110"
  },
  "valor_total": 1250.00,
  "chave_acesso": "35260312345678000190550010001234561123456789"
}
```

**Prompt completo (one-shot):**

```
Você é um extrator de dados de NF-e. Retorne apenas JSON válido, sem markdown.

Exemplo:

Entrada:
[... trecho OCR acima ...]

Saída:
{ ... JSON acima ... }

Regras:
- CNPJ sempre com 14 dígitos, sem pontuação
- Datas no formato ISO 8601 (YYYY-MM-DD)
- Valores numéricos como float, sem "R$"

Agora extraia:
{nf_texto_real}
```

---

## Few-shot Prompting

### Conceito e objetivo

**Few-shot prompting** fornece **vários pares de exemplo** `(entrada → saída)` antes da tarefa real. O modelo aprende padrões implícitos a partir da diversidade dos exemplos: layouts diferentes, campos opcionais ausentes, notas de serviço vs. produto, etc.

O objetivo é **aumentar a generalização** e a **consistência** quando a entrada varia muito, sem fine-tuning do modelo.

### Como funciona

1. Seleciona-se um conjunto de **N exemplos** (tipicamente 2 a 8, dependendo do limite de contexto).
2. Cada exemplo mostra uma variação relevante (layout, campos faltando, múltiplos itens).
3. O modelo identifica invariantes (sempre extrair CNPJ) e adaptações (campo "IE" vs. "Inscrição Estadual").
4. Processa-se o documento alvo seguindo o padrão consolidado.

```python
EXEMPLOS = [
    {"entrada": "...", "saida": {...}},
    {"entrada": "...", "saida": {...}},
    {"entrada": "...", "saida": {...}},
]

def montar_prompt_few_shot(nf_texto: str) -> str:
    blocos = []
    for i, ex in enumerate(EXEMPLOS, 1):
        blocos.append(f"Exemplo {i}:\nEntrada:\n{ex['entrada']}\n\nSaída:\n{json.dumps(ex['saida'])}")
    blocos.append(f"Agora extraia:\n{nf_texto}")
    return "\n\n---\n\n".join(blocos)
```

### Quando utilizar

| Cenário | Indicado? |
|---------|-----------|
| DANFEs de ERPs diferentes (TOTVS, SAP, Omie, etc.) | Sim |
| Campos opcionais ou nomenclaturas distintas | Sim |
| NF-e (produto) e NFS-e (serviço) no mesmo pipeline | Sim |
| Precisão insuficiente com one-shot | Sim |
| Contexto limitado ou custo por token crítico | Use poucos exemplos (2–3) bem escolhidos |
| Exemplos difíceis de curar ou manter atualizados | Avalie CoT ou pós-processamento |

### Vantagens e desvantagens

| Vantagens | Desvantagens |
|-----------|--------------|
| Maior robustez a variações de layout e redação | Mais tokens → maior custo e latência |
| Reduz erros de formato quando exemplos são diversos | Curadoria de exemplos exige esforço contínuo |
| Não exige retreinar o modelo | Exemplos enviesados propagam viés (ex.: só NFs de SP) |
| Complementa validações determinísticas no código | Limite de contexto restringe quantidade de exemplos |

### Exemplos práticos — extração de NF

#### Exemplo 1 — Variação de layout (mesmo dado, rótulos diferentes)

**Exemplo A — rótulo "Valor Total":**

```
Valor Total da Nota: R$ 500,00
```

**Exemplo B — rótulo "Total Geral":**

```
Total Geral.................. R$ 500,00
```

**Saída esperada (ambos):**

```json
{ "valor_total": 500.00 }
```

#### Exemplo 2 — Campo ausente

**Entrada (NF simplificada, sem destinatário explícito):**

```
Emitente: LOJA XYZ  CNPJ: 11.222.333/0001-44
Valor Total: R$ 89,90
```

**Saída:**

```json
{
  "emitente": { "razao_social": "LOJA XYZ", "cnpj": "11222333000144" },
  "destinatario": null,
  "valor_total": 89.90
}
```

#### Exemplo 3 — Lista de itens

**Entrada:**

```
Item 1 - Notebook    Qtd: 2    V.Unit: 3.000,00    Total: 6.000,00
Item 2 - Mouse       Qtd: 2    V.Unit: 50,00       Total: 100,00
```

**Saída:**

```json
{
  "itens": [
    { "descricao": "Notebook", "quantidade": 2, "valor_unitario": 3000.00, "valor_total": 6000.00 },
    { "descricao": "Mouse", "quantidade": 2, "valor_unitario": 50.00, "valor_total": 100.00 }
  ]
}
```

**Prompt few-shot resumido:**

```
Extraia dados de NF-e em JSON. Use null para campos ausentes.

[Exemplo 1: layout padrão com destinatário]
[Exemplo 2: sem destinatário]
[Exemplo 3: com lista de itens]

Documento:
{nf_texto}
```

**Dica:** versionar exemplos no LangSmith permite evoluir o few-shot sem redeploy, desde que o pipeline carregue o prompt atualizado via um módulo de loader dedicado.

---

## Chain of Thought (CoT)

### Conceito e objetivo

**Chain of Thought (CoT)** — *cadeia de raciocínio* — instrui o modelo a **explicitar passos intermediários de raciocínio** antes de entregar a resposta final. Em vez de pular direto ao JSON, o LLM descreve como localizou cada campo, resolveu ambiguidades e aplicou regras de negócio.

O objetivo é melhorar tarefas que exigem **lógica multi-etapa**: validação de dígitos verificadores, reconciliação valor total vs. soma dos itens, identificação de emitente vs. transportadora, etc.

Variantes comuns:

| Variante | Descrição |
|----------|-----------|
| **Zero-shot CoT** | Acrescenta frases como *"Pense passo a passo"* sem exemplos |
| **Few-shot CoT** | Exemplos incluem raciocínio + resposta final |
| **Structured CoT** | Passos numerados ou checklist fixo no prompt |

### Como funciona

1. O prompt pede **raciocínio explícito** (passos numerados ou seções).
2. O modelo gera texto intermediário (chain of thought).
3. Em seguida, produz a **resposta final** estruturada (JSON).
4. Em produção, muitas vezes só a parte final é persistida; o raciocínio vai para logs/traces (LangSmith).

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", """Extraia dados de NF-e.
Siga estas etapas antes do JSON final:
1. Identifique tipo de documento (NF-e, NFS-e, cupom).
2. Localize emitente e destinatário.
3. Extraia valores e datas.
4. Valide consistência (soma itens ≈ total, CNPJ 14 dígitos).
5. Retorne JSON."""),
    ("human", "{nf_texto}"),
])
```

Com **structured output** (Pydantic + LangChain), o raciocínio pode ir em um campo separado:

```json
{
  "raciocinio": "Passo 1: ... Passo 4: soma dos itens 6100 = total 6100, OK.",
  "dados": { "valor_total": 6100.00, "...": "..." }
}
```

### Quando utilizar

| Cenário | Indicado? |
|---------|-----------|
| Validação cruzada (total vs. itens, impostos) | Sim |
| Documentos com OCR ruidoso ou campos conflitantes | Sim |
| Auditoria e explicabilidade para o time/usuário | Sim |
| Debugging de extrações incorretas (trace no LangSmith) | Sim |
| Latência e custo são prioridade absoluta | Prefira CoT só onde necessário |
| Resposta deve ser apenas JSON mínimo | Use CoT interno + strip do raciocínio na API |

### Vantagens e desvantagens

| Vantagens | Desvantagens |
|-----------|--------------|
| Maior acurácia em tarefas com múltiplas regras | Mais tokens e tempo de resposta |
| Raciocínio auditável (útil em apresentação para o time) | Risco de "alucinar" passos plausíveis porém errados |
| Facilita identificar *onde* o modelo errou | Parsing mais complexo se misturar texto livre e JSON |
| Combina bem com few-shot (exemplos com raciocínio) | Nem todo modelo pequeno segue CoT de forma confiável |

### Exemplos práticos — extração de NF

#### Exemplo 1 — Zero-shot CoT

**Prompt:**

```
Analise a Nota Fiscal abaixo. Pense passo a passo:
1. Confirme se é NF-e ou outro tipo.
2. Extraia CNPJs e normalize para 14 dígitos.
3. Verifique se a soma dos itens bate com o valor total.
4. Só então produza o JSON final.

NF:
{nf_texto}
```

**Resposta ilustrativa do modelo:**

```
Passo 1: Trata-se de NF-e modelo 55 (presença de chave de acesso 44 dígitos).
Passo 2: Emitente CNPJ "12.345.678/0001-90" → 12345678000190.
Passo 3: Item1 6000 + Item2 100 = 6100; total informado R$ 6.100,00 → consistente.
Passo 4: JSON abaixo.

{"numero": "789", "valor_total": 6100.00, ...}
```

#### Exemplo 2 — Few-shot CoT (recomendado para produção)

**Exemplo no prompt:**

```
Entrada:
Emitente CNPJ: 12.345.678/0001-90
Total NF: R$ 100,00
Item 1 Total: R$ 60,00
Item 2 Total: R$ 50,00

Raciocínio:
- CNPJ emitente: 12345678000190 (14 dígitos).
- Soma itens: 60 + 50 = 110 ≠ 100 → inconsistência; priorizo total da NF e marco alerta.

Saída:
{
  "emitente": { "cnpj": "12345678000190" },
  "valor_total": 100.00,
  "alertas": ["soma_itens_diverge_total"]
}
```

#### Exemplo 3 — Integração com LangChain (conceitual)

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

class ExtracaoNF(BaseModel):
    raciocinio: str = Field(description="Passos de raciocínio antes da extração")
    numero: str | None = None
    valor_total: float | None = None
    chave_acesso: str | None = None
    alertas: list[str] = Field(default_factory=list)

parser = PydanticOutputParser(pydantic_object=ExtracaoNF)

prompt = ChatPromptTemplate.from_messages([
    ("system", "Extraia dados de NF-e. {format_instructions}"),
    ("human", "{nf_texto}"),
]).partial(format_instructions=parser.get_format_instructions())
```

O campo `raciocinio` documenta a cadeia de pensamento; `alertas` captura inconsistências detectadas no CoT.

---

## Comparativo rápido

| Critério | One-shot | Few-shot | Chain of Thought |
|----------|----------|----------|------------------|
| **Complexidade do prompt** | Baixa | Média | Média–alta |
| **Tokens consumidos** | Baixo | Médio–alto | Alto |
| **Variação de layout** | Limitada | Boa | Boa (com regras explícitas) |
| **Explicabilidade** | Baixa | Baixa | Alta |
| **Manutenção** | Fácil | Exemplos precisam curadoria | Regras + opcionalmente exemplos |
| **Melhor para NF** | MVP, layout único | Múltiplos ERPs/formatos | Validação, OCR ruim, auditoria |


## Referências

- [LangChain — Prompt Templates](https://python.langchain.com/docs/concepts/prompt_templates/)
- [Wei et al. — Chain-of-Thought Prompting (2022)](https://arxiv.org/abs/2201.11903)
- [Brown et al. — Language Models are Few-Shot Learners (GPT-3, 2020)](https://arxiv.org/abs/2005.14165)
