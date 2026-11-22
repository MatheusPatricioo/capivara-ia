from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
PROMPT_FILE_EXTENSION = ".md"


class PromptNotFoundError(Exception):
    """Raised when there is no prompt file with the requested name."""


def load_prompt(prompt_name: str, prompts_dir: Path = PROMPTS_DIR) -> str:
    prompt_file = prompts_dir / f"{prompt_name}{PROMPT_FILE_EXTENSION}"
    if not prompt_file.is_file():
        raise PromptNotFoundError(f"prompt file not found: {prompt_file}")
    return prompt_file.read_text(encoding="utf-8").strip()
