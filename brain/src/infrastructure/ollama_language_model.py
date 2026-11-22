import httpx

from src.domain.language_model import ChatMessage, LanguageModelError


class OllamaLanguageModel:
    def __init__(self, client: httpx.Client, model: str) -> None:
        self._client = client
        self._model = model

    def chat(self, messages: list[ChatMessage]) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": message.role.value, "content": message.content} for message in messages
            ],
            "stream": False,
        }
        try:
            response = self._client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise LanguageModelError(f"Could not get a reply from Ollama: {error}") from error
        return self._extract_content(response)

    @staticmethod
    def _extract_content(response: httpx.Response) -> str:
        try:
            content = response.json()["message"]["content"]
        except (ValueError, KeyError, TypeError) as error:
            raise LanguageModelError("Unexpected response format from Ollama") from error
        if not isinstance(content, str):
            raise LanguageModelError("Unexpected response format from Ollama")
        return content
