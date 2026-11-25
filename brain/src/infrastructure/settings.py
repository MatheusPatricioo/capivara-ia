from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.domain.feelings.needs import NeedRhythm
from src.domain.feelings.temperament import Temperament
from src.infrastructure.ollama_language_model import OllamaGenerationOptions
from src.infrastructure.postgres_discovery_memory import SearchMode, memory_conninfo

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / "brain" / ".env"

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout_seconds: float = 120.0
    ollama_num_predict: int = Field(default=300, gt=0)
    ollama_temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    ollama_repeat_penalty: float = Field(default=1.1, gt=0.0)
    ollama_embedding_model: str = "nomic-embed-text"
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
    # Long-term memory: PostgreSQL + pgvector from compose.yaml. No default password:
    # it lives only in brain/.env.
    memory_db_host: str = "127.0.0.1"
    memory_db_port: int = Field(default=5432, gt=0, lt=65536)
    memory_db_name: str = "capybara_memory"
    memory_db_user: str = "capybara"
    memory_db_password: SecretStr = SecretStr("")
    # How long a memory call waits for a database connection before giving up.
    memory_db_timeout_seconds: float = Field(default=5.0, gt=0)
    # RAG pipeline (measured step by step with python -m src.run_evals --suite retrieval).
    # With rerank, discoveries below this similarity are not even offered to the model;
    # without rerank, the closest one counts only when it reaches it. See .env.example.
    memory_recall_min_similarity: float = Field(default=0.50, ge=0.0, le=1.0)
    memory_search_mode: SearchMode = SearchMode.HYBRID
    memory_task_prefixes: bool = True
    memory_query_rewriting: bool = False
    memory_rerank: bool = True
    # Agentic RAG: offer the recall_memory tool. Off by default: qwen2.5:7b never called it
    # in the evals, and the extra tool made it save fewer discoveries.
    memory_recall_tool: bool = False
    # A new suggestion repeats an earlier one when their cosine similarity reaches this.
    # 0.80 was measured with nomic-embed-text; see .env.example.
    suggestion_repeat_min_similarity: float = Field(default=0.80, ge=0.0, le=1.0)
    # Feelings: her emotional life, kept in <DISCOVERIES_DIR>/feelings.json.
    feelings_enabled: bool = True
    # Speeds up how fast her needs empty (10 = ten times faster), to watch her live.
    feelings_time_scale: float = Field(default=1.0, gt=0)
    # Her temperament, each trait from 0 to 1. The defaults are a curious, cheerful capybara.
    temperament_curiosity: float = Field(default=0.9, ge=0.0, le=1.0)
    temperament_cheerfulness: float = Field(default=0.8, ge=0.0, le=1.0)
    temperament_patience: float = Field(default=0.6, ge=0.0, le=1.0)
    temperament_sensitivity: float = Field(default=0.5, ge=0.0, le=1.0)
    temperament_resilience: float = Field(default=0.7, ge=0.0, le=1.0)
    log_level: LogLevel = "INFO"
    log_file: Path = PROJECT_ROOT / "logs" / "capybara.log"

    def ollama_generation_options(self) -> OllamaGenerationOptions:
        return OllamaGenerationOptions(
            num_predict=self.ollama_num_predict,
            temperature=self.ollama_temperature,
            repeat_penalty=self.ollama_repeat_penalty,
        )

    def temperament(self) -> Temperament:
        return Temperament(
            curiosity=self.temperament_curiosity,
            cheerfulness=self.temperament_cheerfulness,
            patience=self.temperament_patience,
            sensitivity=self.temperament_sensitivity,
            resilience=self.temperament_resilience,
        )

    def need_rhythm(self) -> NeedRhythm:
        return NeedRhythm(time_scale=self.feelings_time_scale)

    def memory_db_conninfo(self) -> str:
        return memory_conninfo(
            host=self.memory_db_host,
            port=self.memory_db_port,
            database=self.memory_db_name,
            user=self.memory_db_user,
            password=self.memory_db_password.get_secret_value(),
        )
