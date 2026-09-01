"""Contrato JSON da extração de Nota Fiscal (modelos Pydantic).

Campos que o LLM não conseguir extrair (ausentes ou incertos) devem ser
``null`` — nunca string vazia nem valor inventado. Inconsistências
(ex.: soma dos produtos diferente do total) não invalidam o schema:
ficam em ``ExtracaoResponse.inconsistencias``.
"""

from pydantic import BaseModel, Field

from extracao_nf.domain.enums import TipoDocumento, TipoInconsistencia


class Emitente(BaseModel):
    """Dados do emitente (quem emite a nota)."""

    razao_social: str | None = Field(
        default=None,
        description="Razão social do emitente. Use null se não estiver legível no documento.",
    )
    nome_fantasia: str | None = Field(
        default=None,
        description="Nome fantasia do emitente, se houver. Use null se ausente.",
    )
    cnpj: str | None = Field(
        default=None,
        description="CNPJ do emitente com 14 dígitos, sem pontuação. Use null se ausente.",
    )
    inscricao_estadual: str | None = Field(
        default=None,
        description="Inscrição estadual do emitente. Use null se ausente ou 'ISENTO'.",
    )
    uf: str | None = Field(
        default=None,
        description="UF (sigla de 2 letras) do emitente. Use null se ausente.",
    )
    municipio: str | None = Field(
        default=None,
        description="Município do emitente. Use null se ausente.",
    )
    endereco: str | None = Field(
        default=None,
        description=(
            "Endereço completo do emitente (logradouro, número, bairro, CEP). Use null se ausente."
        ),
    )


class Destinatario(BaseModel):
    """Dados do destinatário. Pode ser ``null`` no pai se a NF não o trouxer."""

    razao_social: str | None = Field(
        default=None,
        description="Razão social ou nome do destinatário. Use null se não estiver legível.",
    )
    cnpj: str | None = Field(
        default=None,
        description=(
            "CNPJ do destinatário com 14 dígitos, sem pontuação. Use null se for CPF ou se ausente."
        ),
    )
    cpf: str | None = Field(
        default=None,
        description=(
            "CPF do destinatário com 11 dígitos, sem pontuação. Use null se for CNPJ ou se ausente."
        ),
    )
    inscricao_estadual: str | None = Field(
        default=None,
        description="Inscrição estadual do destinatário. Use null se ausente.",
    )
    uf: str | None = Field(
        default=None,
        description="UF (sigla de 2 letras) do destinatário. Use null se ausente.",
    )
    municipio: str | None = Field(
        default=None,
        description="Município do destinatário. Use null se ausente.",
    )
    endereco: str | None = Field(
        default=None,
        description="Endereço completo do destinatário. Use null se ausente.",
    )


class DadosNota(BaseModel):
    """Identificação da nota (número, série, datas, chave)."""

    numero: str | None = Field(
        default=None,
        description="Número da nota, sem zeros à esquerda desnecessários. Use null se ausente.",
    )
    serie: str | None = Field(
        default=None,
        description="Série da nota. Use null se ausente.",
    )
    modelo: str | None = Field(
        default=None,
        description=(
            "Modelo do documento (ex.: '55' para NF-e, '65' para NFC-e). Use null se ausente."
        ),
    )
    tipo_documento: TipoDocumento | None = Field(
        default=None,
        description="Tipo do documento fiscal (NF-e, NFS-e, NFC-e ou outro). Use null se incerto.",
    )
    data_emissao: str | None = Field(
        default=None,
        description="Data de emissão no formato ISO 8601 (YYYY-MM-DD). Use null se ausente.",
    )
    natureza_operacao: str | None = Field(
        default=None,
        description="Natureza da operação (ex.: 'Venda de mercadoria'). Use null se ausente.",
    )
    chave_acesso: str | None = Field(
        default=None,
        description="Chave de acesso da NF-e com 44 dígitos, sem espaços. Use null se ausente.",
    )


class Valores(BaseModel):
    """Totais e impostos da nota. Valores numéricos como float, sem 'R$'."""

    valor_produtos: float | None = Field(
        default=None,
        description="Soma dos valores dos produtos/serviços. Use null se ausente.",
    )
    valor_frete: float | None = Field(
        default=None,
        description="Valor do frete. Use null se ausente.",
    )
    valor_seguro: float | None = Field(
        default=None,
        description="Valor do seguro. Use null se ausente.",
    )
    valor_desconto: float | None = Field(
        default=None,
        description="Valor total de desconto. Use null se ausente.",
    )
    valor_icms: float | None = Field(
        default=None,
        description="Valor do ICMS. Use null se ausente.",
    )
    valor_ipi: float | None = Field(
        default=None,
        description="Valor do IPI. Use null se ausente.",
    )
    valor_pis: float | None = Field(
        default=None,
        description="Valor do PIS. Use null se ausente.",
    )
    valor_cofins: float | None = Field(
        default=None,
        description="Valor do COFINS. Use null se ausente.",
    )
    valor_total_nota: float | None = Field(
        default=None,
        description="Valor total da nota fiscal. Use null se ausente.",
    )


class Produto(BaseModel):
    """Um item (produto ou serviço) da nota."""

    codigo: str | None = Field(
        default=None,
        description="Código do produto no emitente. Use null se ausente.",
    )
    descricao: str | None = Field(
        default=None,
        description="Descrição do produto/serviço. Use null se ausente.",
    )
    ncm: str | None = Field(
        default=None,
        description="NCM (8 dígitos, sem pontuação). Use null se ausente.",
    )
    cfop: str | None = Field(
        default=None,
        description="CFOP (4 dígitos). Use null se ausente.",
    )
    unidade: str | None = Field(
        default=None,
        description="Unidade comercial (UN, KG, CX, etc.). Use null se ausente.",
    )
    quantidade: float | None = Field(
        default=None,
        description="Quantidade comercializada. Use null se ausente.",
    )
    valor_unitario: float | None = Field(
        default=None,
        description="Valor unitário do item. Use null se ausente.",
    )
    valor_total: float | None = Field(
        default=None,
        description=(
            "Valor total do item (quantidade * unitário, já com descontos do item). "
            "Use null se ausente."
        ),
    )


class Inconsistencia(BaseModel):
    """Inconsistência detectada de forma determinística após a extração.

    Não representa campo ausente (isso é ``null`` no campo correspondente).
    """

    tipo: TipoInconsistencia = Field(
        description="Classificação da inconsistência",
    )
    campo: str | None = Field(
        default=None,
        description="Campo relacionado, em notação pontuada (ex.: 'valores.valor_total_nota').",
    )
    descricao: str = Field(
        description="Descrição legível da inconsistência encontrada",
    )
    valor_esperado: str | None = Field(
        default=None,
        description="Valor esperado (ex.: soma dos produtos), se aplicável",
    )
    valor_encontrado: str | None = Field(
        default=None,
        description="Valor encontrado no documento (ex.: total da nota), se aplicável",
    )


class NotaFiscalExtraida(BaseModel):
    """Schema completo extraído da nota — contrato preenchido pelo LLM.

    Objetos aninhados existem mesmo quando todos os campos internos são null.
    ``destinatario`` pode ser null quando a NF não traz destinatário.
    """

    emitente: Emitente = Field(
        default_factory=Emitente,
        description="Dados do emitente. Preencha os campos encontrados; use null nos demais.",
    )
    destinatario: Destinatario | None = Field(
        default=None,
        description="Dados do destinatário. Use null se a nota não trouxer destinatário.",
    )
    dados_nota: DadosNota = Field(
        default_factory=DadosNota,
        description="Identificação da nota (número, série, data, chave).",
    )
    valores: Valores = Field(
        default_factory=Valores,
        description="Totais e impostos da nota.",
    )
    produtos: list[Produto] = Field(
        default_factory=list,
        description="Itens da nota. Lista vazia se nenhum item for identificável.",
    )


class ExtracaoResponse(BaseModel):
    """Contrato de saída da API POST /extrair-nf.

    Separa dados extraídos (incluindo campos ``null``) das inconsistências
    calculadas depois da extração, que nunca impedem a resposta 200.
    """

    nota_fiscal: NotaFiscalExtraida = Field(
        description="Dados extraídos da nota fiscal",
    )
    inconsistencias: list[Inconsistencia] = Field(
        default_factory=list,
        description=(
            "Inconsistências detectadas após a extração "
            "(ex.: soma dos valor_total dos produtos vs. valores.valor_total_nota). "
            "Lista vazia se não houver divergência."
        ),
    )
