from __future__ import annotations

import json
from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from extracao_nf.core.config import Settings
from extracao_nf.domain.models import NotaFiscalExtraida
from extracao_nf.services.llm_provider import criar_chat_model

_SYSTEM_PROMPT = (
    "Você extrai dados estruturados de Notas Fiscais brasileiras "
    "(NF-e, NFS-e, NFC-e ou similares).\n"
    "\n"
    "Regras obrigatórias:\n"
    "- Preencha apenas o que estiver legível no documento; "
    "use null para campos ausentes ou incertos.\n"
    "- Nunca invente valores, CNPJ/CPF, chave de acesso ou itens.\n"
    "- CNPJ com 14 dígitos e CPF com 11 dígitos, sem pontuação.\n"
    "- Datas no formato ISO 8601 (YYYY-MM-DD).\n"
    "- Valores numéricos como float, sem símbolo R$ e sem milhar com ponto "
    "(ex.: 1250.00).\n"
    "- Chave de acesso da NF-e com 44 dígitos, sem espaços.\n"
    "- Se a nota não trouxer destinatário, use destinatario = null.\n"
    "- A lista produtos deve refletir os itens do documento; "
    "use [] se nenhum item for identificável.\n"
    "- O schema de saída é o contrato Pydantic NotaFiscalExtraida "
    "(emitente, destinatario, dados_nota, valores, produtos)."
)

# why: exemplos da doc de prompting, adaptados ao schema NotaFiscalExtraida
_EXEMPLO_1_ENTRADA = (
    "Emitente: LOJA XYZ  CNPJ: 11.222.333/0001-44\n"
    "Valor Total: R$ 89,90\n"
    "(sem destinatário explícito no documento)"
)

_EXEMPLO_1_SAIDA: dict[str, Any] = {
    "emitente": {
        "razao_social": "LOJA XYZ",
        "nome_fantasia": None,
        "cnpj": "11222333000144",
        "inscricao_estadual": None,
        "uf": None,
        "municipio": None,
        "endereco": None,
    },
    "destinatario": None,
    "dados_nota": {
        "numero": None,
        "serie": None,
        "modelo": None,
        "tipo_documento": None,
        "data_emissao": None,
        "natureza_operacao": None,
        "chave_acesso": None,
    },
    "valores": {
        "valor_produtos": None,
        "valor_frete": None,
        "valor_seguro": None,
        "valor_desconto": None,
        "valor_icms": None,
        "valor_ipi": None,
        "valor_pis": None,
        "valor_cofins": None,
        "valor_total_nota": 89.9,
    },
    "produtos": [],
}

_EXEMPLO_2_ENTRADA = (
    "NOTA FISCAL ELETRÔNICA - NF-e\n"
    "Nº 000.123.456  Série 1  Emissão: 15/03/2026\n"
    "Emitente: ACME LTDA  CNPJ: 12.345.678/0001-90\n"
    "Destinatário: CLIENTE SA  CNPJ: 98.765.432/0001-10\n"
    "Item 1 - Notebook    Qtd: 2    V.Unit: 3.000,00    Total: 6.000,00\n"
    "Item 2 - Mouse       Qtd: 2    V.Unit: 50,00       Total: 100,00\n"
    "Valor Total da Nota: R$ 6.100,00\n"
    "Chave de Acesso: 35260312345678000190550010001234561123456789"
)

_EXEMPLO_2_SAIDA: dict[str, Any] = {
    "emitente": {
        "razao_social": "ACME LTDA",
        "nome_fantasia": None,
        "cnpj": "12345678000190",
        "inscricao_estadual": None,
        "uf": None,
        "municipio": None,
        "endereco": None,
    },
    "destinatario": {
        "razao_social": "CLIENTE SA",
        "cnpj": "98765432000110",
        "cpf": None,
        "inscricao_estadual": None,
        "uf": None,
        "municipio": None,
        "endereco": None,
    },
    "dados_nota": {
        "numero": "123456",
        "serie": "1",
        "modelo": "55",
        "tipo_documento": "NF-e",
        "data_emissao": "2026-03-15",
        "natureza_operacao": None,
        "chave_acesso": "35260312345678000190550010001234561123456789",
    },
    "valores": {
        "valor_produtos": 6100.0,
        "valor_frete": None,
        "valor_seguro": None,
        "valor_desconto": None,
        "valor_icms": None,
        "valor_ipi": None,
        "valor_pis": None,
        "valor_cofins": None,
        "valor_total_nota": 6100.0,
    },
    "produtos": [
        {
            "codigo": None,
            "descricao": "Notebook",
            "ncm": None,
            "cfop": None,
            "unidade": None,
            "quantidade": 2.0,
            "valor_unitario": 3000.0,
            "valor_total": 6000.0,
        },
        {
            "codigo": None,
            "descricao": "Mouse",
            "ncm": None,
            "cfop": None,
            "unidade": None,
            "quantidade": 2.0,
            "valor_unitario": 50.0,
            "valor_total": 100.0,
        },
    ],
}


def _formatar_exemplo(*, indice: int, entrada: str, saida: dict[str, Any]) -> str:
    saida_json = json.dumps(saida, ensure_ascii=False, indent=2)
    return f"Exemplo {indice}:\nEntrada:\n{entrada.strip()}\n\nSaída:\n{saida_json}"


def _bloco_few_shot() -> str:
    partes = [
        _formatar_exemplo(indice=1, entrada=_EXEMPLO_1_ENTRADA, saida=_EXEMPLO_1_SAIDA),
        _formatar_exemplo(indice=2, entrada=_EXEMPLO_2_ENTRADA, saida=_EXEMPLO_2_SAIDA),
    ]
    return "\n\n---\n\n".join(partes)


def construir_prompt() -> ChatPromptTemplate:
    # why: {{ }} evita que chaves do JSON few-shot sejam lidas como variáveis do template
    few_shot = _bloco_few_shot().replace("{", "{{").replace("}", "}}")
    return ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            ("human", few_shot),
            (
                "human",
                [
                    {
                        "type": "text",
                        "text": (
                            "Agora extraia os dados da nota fiscal anexada, "
                            "seguindo o mesmo schema e as regras acima."
                        ),
                    },
                    {"type": "image_url", "image_url": "{data_uri}"},
                ],
            ),
        ]
    )


def montar_chain(
    *,
    settings: Settings,
    llm: BaseChatModel | None = None,
) -> Runnable[dict[str, str], NotaFiscalExtraida]:
    prompt = construir_prompt()
    chat_model = llm if llm is not None else criar_chat_model(settings)
    chain = prompt | chat_model.with_structured_output(NotaFiscalExtraida)
    return cast(Runnable[dict[str, str], NotaFiscalExtraida], chain)
