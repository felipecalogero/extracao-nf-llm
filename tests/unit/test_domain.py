"""Testes unitários dos enums e modelos de domínio da extração de NF."""

import pytest
from pydantic import ValidationError

from extracao_nf.domain.enums import TipoDocumento, TipoInconsistencia
from extracao_nf.domain.models import (
    DadosNota,
    Destinatario,
    Emitente,
    ExtracaoResponse,
    Inconsistencia,
    NotaFiscalExtraida,
    Produto,
    Valores,
)


def test_tipo_documento_deve_conter_os_tipos_fiscais_esperados() -> None:
    """TipoDocumento cobre NF-e, NFS-e, NFC-e e um fallback genérico."""
    assert TipoDocumento.NFE.value == "NF-e"
    assert TipoDocumento.NFSE.value == "NFS-e"
    assert TipoDocumento.NFCE.value == "NFC-e"
    assert TipoDocumento.OUTRO.value == "outro"


def test_tipo_inconsistencia_deve_conter_soma_produtos_diverge_total() -> None:
    """Tipo usado na checagem determinística soma dos itens vs. total da nota."""
    assert TipoInconsistencia.SOMA_PRODUTOS_DIVERGE_TOTAL.value == "soma_produtos_diverge_total"


def test_emitente_deve_aceitar_todos_os_campos_nulos() -> None:
    """Campo não encontrado é null — o objeto emitente continua válido."""
    emitente = Emitente()

    assert emitente.razao_social is None
    assert emitente.cnpj is None
    dumped = emitente.model_dump()
    assert dumped["cnpj"] is None
    assert dumped["inscricao_estadual"] is None


def test_destinatario_ausente_e_representado_por_null_no_pai() -> None:
    """NF sem destinatário: destinatario=null, não um objeto vazio obrigatório."""
    nota = NotaFiscalExtraida()

    assert nota.destinatario is None
    assert nota.model_dump()["destinatario"] is None


def test_dados_nota_deve_rejeitar_tipo_documento_invalido() -> None:
    """tipo_documento só aceita valores de TipoDocumento."""
    with pytest.raises(ValidationError):
        DadosNota.model_validate({"tipo_documento": "DANFE"})


def test_nota_fiscal_completa_deve_serializar_o_contrato_esperado() -> None:
    """Serialização JSON preserva aninhamento, floats e lista de produtos."""
    nota = NotaFiscalExtraida(
        emitente=Emitente(razao_social="ACME LTDA", cnpj="12345678000190"),
        destinatario=Destinatario(razao_social="CLIENTE SA", cnpj="98765432000110"),
        dados_nota=DadosNota(
            numero="123456",
            serie="1",
            tipo_documento=TipoDocumento.NFE,
            data_emissao="2026-03-15",
            chave_acesso="35260312345678000190550010001234561123456789",
        ),
        valores=Valores(valor_produtos=1250.0, valor_total_nota=1250.0),
        produtos=[
            Produto(
                descricao="Notebook",
                quantidade=2,
                valor_unitario=3000.0,
                valor_total=6000.0,
            ),
            Produto(
                descricao="Mouse",
                quantidade=2,
                valor_unitario=50.0,
                valor_total=100.0,
            ),
        ],
    )

    dumped = nota.model_dump()
    assert dumped["emitente"]["cnpj"] == "12345678000190"
    assert dumped["dados_nota"]["data_emissao"] == "2026-03-15"
    assert dumped["dados_nota"]["tipo_documento"] == "NF-e"
    assert dumped["valores"]["valor_total_nota"] == 1250.0
    assert len(dumped["produtos"]) == 2
    assert dumped["produtos"][0]["descricao"] == "Notebook"
    assert dumped["produtos"][1]["valor_total"] == 100.0

    restaurada = NotaFiscalExtraida.model_validate(dumped)
    assert restaurada.emitente.cnpj == "12345678000190"
    assert restaurada.produtos[1].descricao == "Mouse"


def test_campo_ausente_permanece_null_e_nao_e_inconsistencia() -> None:
    """Campo incerto/ausente vira null; inconsistencias ficam na resposta da API."""
    nota = NotaFiscalExtraida(
        emitente=Emitente(razao_social="LOJA XYZ", cnpj="11222333000144"),
        valores=Valores(valor_total_nota=89.9),
    )
    resposta = ExtracaoResponse(nota_fiscal=nota)

    assert nota.destinatario is None
    assert nota.dados_nota.chave_acesso is None
    assert nota.produtos == []
    assert resposta.inconsistencias == []
    assert resposta.model_dump()["inconsistencias"] == []


def test_inconsistencia_exige_tipo_e_descricao() -> None:
    """Inconsistencia sem tipo ou descricao não é um contrato válido."""
    with pytest.raises(ValidationError):
        Inconsistencia(tipo=TipoInconsistencia.SOMA_PRODUTOS_DIVERGE_TOTAL)  # type: ignore[call-arg]

    inconsistencia = Inconsistencia(
        tipo=TipoInconsistencia.SOMA_PRODUTOS_DIVERGE_TOTAL,
        campo="valores.valor_total_nota",
        descricao="Soma dos produtos (110.00) diverge do total da nota (100.00)",
        valor_esperado="110.00",
        valor_encontrado="100.00",
    )
    assert inconsistencia.tipo == TipoInconsistencia.SOMA_PRODUTOS_DIVERGE_TOTAL
    assert inconsistencia.campo == "valores.valor_total_nota"


def test_extracao_response_separa_dados_extraidos_de_inconsistencias() -> None:
    """A API devolve a NF extraída mesmo quando há divergência de valores."""
    nota = NotaFiscalExtraida(
        valores=Valores(valor_total_nota=100.0),
        produtos=[
            Produto(descricao="Item A", valor_total=60.0),
            Produto(descricao="Item B", valor_total=50.0),
        ],
    )
    resposta = ExtracaoResponse(
        nota_fiscal=nota,
        inconsistencias=[
            Inconsistencia(
                tipo=TipoInconsistencia.SOMA_PRODUTOS_DIVERGE_TOTAL,
                campo="valores.valor_total_nota",
                descricao="Soma dos produtos diverge do total da nota",
                valor_esperado="110.0",
                valor_encontrado="100.0",
            )
        ],
    )

    dumped = resposta.model_dump()
    assert dumped["nota_fiscal"]["valores"]["valor_total_nota"] == 100.0
    assert len(dumped["inconsistencias"]) == 1
    assert dumped["inconsistencias"][0]["tipo"] == "soma_produtos_diverge_total"
    restaurada = ExtracaoResponse.model_validate(dumped)
    assert restaurada.inconsistencias[0].valor_esperado == "110.0"
