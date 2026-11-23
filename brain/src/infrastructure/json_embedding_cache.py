import json
import logging
from pathlib import Path

from pydantic import BaseModel, ValidationError

from src.domain.text_embedding import Embedding

logger = logging.getLogger(__name__)


class _CacheFile(BaseModel):
    model: str
    embeddings: dict[str, list[float]]


class JsonEmbeddingCache:
    """Embeddings saved in a JSON file, keyed by the embedded text.

    Vectors from different models cannot be compared, so the file remembers which model
    made them: when the model changes, the old cache is ignored and rebuilt.
    """

    def __init__(self, file_path: Path, model: str) -> None:
        self._file_path = file_path
        self._model = model

    def load(self) -> dict[str, Embedding]:
        if not self._file_path.is_file():
            return {}
        try:
            cache_file = _CacheFile.model_validate_json(self._file_path.read_bytes())
        except (OSError, ValidationError) as error:
            logger.warning("Ignoring an unreadable embedding cache %s: %s", self._file_path, error)
            return {}
        if cache_file.model != self._model:
            return {}
        return {text: tuple(vector) for text, vector in cache_file.embeddings.items()}

    def save(self, embeddings: dict[str, Embedding]) -> None:
        content = {
            "model": self._model,
            "embeddings": {text: list(vector) for text, vector in embeddings.items()},
        }
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
