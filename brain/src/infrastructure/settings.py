from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.domain.feelings.needs import NeedRhythm
from src.domain.feelings.temperament import Temperament
from src.domain.letter import LetterRhythm
from src.domain.weather import Sky
from src.domain.world_clock import ClockMode, WorldClock
from src.infrastructure.ollama_language_model import OllamaGenerationOptions
from src.infrastructure.postgres_discovery_memory import SearchMode, memory_conninfo

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / "brain" / ".env"

SECONDS_PER_MINUTE = 60.0

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
    # When the search finds nothing, she tries Wikipedia. Its robot policy asks for a
    # contact (a link or e-mail) in the User-Agent; while empty, the fallback stays off.
    wikipedia_contact: str = ""
    wikipedia_language: str = "pt"
    wikipedia_timeout_seconds: float = Field(default=10.0, gt=0)
    discoveries_dir: Path = PROJECT_ROOT / "discoveries"
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
    # Letters: when she misses her creator, she writes to him (needs FEELINGS_ENABLED).
    letters_enabled: bool = True
    letter_min_hours_between: float = Field(default=20.0, ge=0)
    letter_max_unread: int = Field(default=3, gt=0)
    # Her diary (one file per day in "diario"): how many of the latest days the world shows.
    diary_shown_days: int = Field(default=14, gt=0)
    # Day and night in her world: "real" follows the wall clock, "fast" squeezes a whole
    # day into world_fast_day_minutes real minutes, for quick tests.
    world_clock_mode: ClockMode = ClockMode.REAL
    world_fast_day_minutes: float = Field(default=60.0, gt=0)
    # Real weather from Open-Meteo (free, no key): when it rains there, it rains in her world.
    weather_enabled: bool = True
    weather_place_name: str = "Belo Horizonte"
    weather_latitude: float = Field(default=-19.9167, ge=-90.0, le=90.0)
    weather_longitude: float = Field(default=-43.9345, ge=-180.0, le=180.0)
    weather_timeout_seconds: float = Field(default=10.0, gt=0)
    weather_refresh_minutes: float = Field(default=15.0, gt=0)
    # A fixed sky (like "rain") instead of the real one, to test without waiting for rain.
    weather_override: Sky | None = None
    # Voice in the chat (python -m src.chat_with_capybara --voz), all local and offline:
    # Piper speaks with the voice file below, faster-whisper listens with a Whisper model.
    voice_model_path: Path = PROJECT_ROOT / "brain" / "voices" / "pt_BR-faber-medium.onnx"
    # Whisper size: tiny, base, small, medium or large-v3. Bigger hears better but is slower.
    speech_recognition_model: str = "small"
    speech_recognition_language: str = "pt"
    # "cpu" works everywhere; "cuda" uses an NVIDIA graphics card.
    speech_recognition_device: str = "cpu"
    # How the model numbers are stored: int8 is light on the CPU, float16 suits the GPU.
    speech_recognition_compute_type: str = "int8"
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

    def letter_rhythm(self) -> LetterRhythm:
        return LetterRhythm(
            min_hours_between=self.letter_min_hours_between, max_unread=self.letter_max_unread
        )

    def world_clock(self) -> WorldClock:
        return WorldClock(
            self.world_clock_mode,
            fast_day_seconds=self.world_fast_day_minutes * SECONDS_PER_MINUTE,
        )

    def memory_db_conninfo(self) -> str:
        return memory_conninfo(
            host=self.memory_db_host,
            port=self.memory_db_port,
            database=self.memory_db_name,
            user=self.memory_db_user,
            password=self.memory_db_password.get_secret_value(),
        )
