"""Testes unitários do provider Gemini e da chain de extração (Parte 5)."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.runnables import RunnableLambda

from extracao_nf.core.config import Settings
from extracao_nf.domain.models import NotaFiscalExtraida
from extracao_nf.services.llm_provider import criar_chat_model
from extracao_nf.services.prompt_builder import construir_prompt, montar_chain
from tests.fakes import fake_llm_com_nota, nota_fiscal_exemplo, settings_teste


def test_criar_chat_model_exige_api_key() -> None:
    """Sem GOOGLE_API_KEY o provider deve falhar de forma explícita."""
    settings = Settings(environment="test", google_api_key=None)

    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        criar_chat_model(settings)


def test_criar_chat_model_rejeita_chave_vazia() -> None:
    """Chave em branco deve ser tratada como não configurada."""
    settings = settings_teste(google_api_key="   ")

    with pytest.raises(ValueError, match="vazia"):
        criar_chat_model(settings)


def test_criar_chat_model_com_settings() -> None:
    """Factory deve criar ChatGoogleGenerativeAI com modelo e temperatura das settings."""
    settings = settings_teste()
    llm = criar_chat_model(settings)

    assert llm.model == "gemini-3.8-flash"
    assert llm.temperature == 0.0
    assert llm.timeout == 30.0


def test_construir_prompt_inclui_few_shot_e_data_uri() -> None:
    """Prompt deve trazer exemplos (campo ausente + produtos) e aceitar data_uri."""
    prompt = construir_prompt()
    mensagens = prompt.invoke({"data_uri": "data:application/pdf;base64,abc123"})

    textos = []
    for mensagem in mensagens.to_messages():
        if isinstance(mensagem.content, str):
            textos.append(mensagem.content)
        elif isinstance(mensagem.content, list):
            for parte in mensagem.content:
                if isinstance(parte, dict) and parte.get("type") == "text":
                    textos.append(str(parte.get("text", "")))

    blob = "\n".join(textos)
    assert "destinatario" in blob
    assert "Notebook" in blob
    assert "null" in blob.lower() or "None" in blob or '"destinatario": null' in blob

    humana_final = mensagens.to_messages()[-1]
    assert isinstance(humana_final.content, list)
    imagem = next(
        parte
        for parte in humana_final.content
        if isinstance(parte, dict) and parte.get("type") == "image_url"
    )
    image_url = imagem["image_url"]
    url = image_url["url"] if isinstance(image_url, dict) else image_url
    assert url == "data:application/pdf;base64,abc123"


def test_montar_chain_com_llm_mockado_retorna_nota_fiscal() -> None:
    """Chain com LLM mockado deve devolver NotaFiscalExtraida a partir do data_uri."""
    nota_esperada = nota_fiscal_exemplo()
    llm_fake = fake_llm_com_nota(nota_esperada)

    chain = montar_chain(settings=settings_teste(), llm=llm_fake)
    resultado: NotaFiscalExtraida = chain.invoke({"data_uri": "data:image/png;base64,fake"})

    assert isinstance(resultado, NotaFiscalExtraida)
    assert resultado.emitente.razao_social == "ACME LTDA"
    assert resultado.destinatario is None
    assert resultado.valores.valor_total_nota == 1250.0
    assert len(resultado.produtos) == 1
    assert resultado.produtos[0].descricao == "Notebook"
    llm_fake.with_structured_output.assert_called_once_with(NotaFiscalExtraida)


def test_montar_chain_usa_criar_chat_model_quando_llm_nao_injetado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem llm injetado, montar_chain deve delegar a criar_chat_model."""
    chamada: dict[str, Any] = {}

    def _fake_criar(settings: Settings) -> MagicMock:
        chamada["settings"] = settings
        llm = MagicMock()
        llm.with_structured_output.return_value = RunnableLambda(lambda _: NotaFiscalExtraida())
        return llm

    monkeypatch.setattr(
        "extracao_nf.services.prompt_builder.criar_chat_model",
        _fake_criar,
    )

    settings = settings_teste()
    chain = montar_chain(settings=settings)
    resultado = chain.invoke({"data_uri": "data:application/pdf;base64,x"})

    assert chamada["settings"] is settings
    assert isinstance(resultado, NotaFiscalExtraida)
