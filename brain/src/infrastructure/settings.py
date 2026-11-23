from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.infrastructure.ollama_language_model import OllamaGenerationOptions

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / "brain" / ".env"

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout_seconds: float = 120.0
    ollama_num_predict: int = Field(default=300, gt=0)
    ollama_structured_num_predict: int = Field(default=800, gt=0)
    ollama_temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    ollama_repeat_penalty: float = Field(default=1.1, gt=0.0)
    ollama_embedding_model: str = "nomic-embed-text"
    # How far the closest doodle category must be ahead of the second one to be drawn.
    doodle_min_margin: float = Field(default=0.016, ge=0.0)
    max_tool_steps: int = 5
    web_search_backend: str = "duckduckgo"
    # DuckDuckGo region code; "br-pt" brings Brazilian pages first.
    web_search_region: str = "br-pt"
    discoveries_dir: Path = PROJECT_ROOT / "discoveries"
    chalkboard_capacity: int = Field(default=3, gt=0)
    world_server_host: str = "127.0.0.1"
    world_server_port: int = Field(default=8765, gt=0, lt=65536)
    autonomous_cycle_interval_seconds: float = Field(default=120.0, gt=0)
    max_tokens_per_hour: int = Field(default=60000, gt=0)
    max_remembered_discoveries: int = Field(default=20, gt=0)
    attention_capacity: int = Field(default=5, gt=0)
    attention_rest_minutes: float = Field(default=30.0, ge=0)
    log_level: LogLevel = "INFO"
    log_file: Path = PROJECT_ROOT / "logs" / "capybara.log"

    def ollama_generation_options(self) -> OllamaGenerationOptions:
        return OllamaGenerationOptions(
            num_predict=self.ollama_num_predict,
            temperature=self.ollama_temperature,
            repeat_penalty=self.ollama_repeat_penalty,
        )
