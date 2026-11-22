from src.domain.language_model import ChatMessage, LanguageModel, Role


class Conversation:
    def __init__(self, language_model: LanguageModel, system_prompt: str) -> None:
        self._language_model = language_model
        self._history = [ChatMessage(role=Role.SYSTEM, content=system_prompt)]

    @property
    def history(self) -> tuple[ChatMessage, ...]:
        return tuple(self._history)

    def send(self, user_message: str) -> str:
        user_chat_message = ChatMessage(role=Role.USER, content=user_message)
        reply = self._language_model.chat([*self._history, user_chat_message])
        self._history.append(user_chat_message)
        self._history.append(ChatMessage(role=Role.ASSISTANT, content=reply))
        return reply
