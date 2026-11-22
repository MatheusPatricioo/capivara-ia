from src.domain.language_model import ChatMessage, LanguageModel, Role


class AskQuestion:
    def __init__(self, language_model: LanguageModel) -> None:
        self._language_model = language_model

    def execute(self, system_prompt: str, question: str) -> str:
        messages = [
            ChatMessage(role=Role.SYSTEM, content=system_prompt),
            ChatMessage(role=Role.USER, content=question),
        ]
        return self._language_model.chat(messages).content
