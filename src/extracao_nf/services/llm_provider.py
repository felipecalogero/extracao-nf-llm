from langchain_google_genai import ChatGoogleGenerativeAI

from extracao_nf.core.config import Settings


def criar_chat_model(settings: Settings) -> ChatGoogleGenerativeAI:
    if settings.google_api_key is None:
        raise ValueError(
            "GOOGLE_API_KEY não configurada. Defina a variável de ambiente ou o arquivo .env."
        )

    api_key = settings.google_api_key.get_secret_value().strip()
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY está vazia. Defina a variável de ambiente ou o arquivo .env."
        )

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=api_key,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout_seconds,
    )
