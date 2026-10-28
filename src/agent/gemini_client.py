"""Cliente para a API do Google Gemini com suporte a Saídas Estruturadas (Structured Outputs)."""
import logging
from typing import TypeVar
from google import genai
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    """Wrapper para o SDK moderno google-genai com saídas tipadas via Pydantic."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if not api_key:
            raise ValueError(
                "A GEMINI_API_KEY não foi configurada. "
                "Defina a variável no arquivo .env ou no ambiente."
            )
        self.api_key = api_key
        self.model = model
        self.client = genai.Client(api_key=self.api_key)

    def generate_structured(
        self,
        prompt: str,
        system_instruction: str,
        response_schema: type[T],
    ) -> T:
        """Gera resposta do modelo forçando o schema Pydantic via JSON estruturado."""
        logger.debug(f"Enviando prompt ao Gemini ({self.model})...")

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.7,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        if not response.text:
            raise RuntimeError("O Gemini retornou uma resposta vazia.")

        # Validação e conversão direta no modelo Pydantic
        return response_schema.model_validate_json(response.text)
