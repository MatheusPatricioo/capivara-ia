import hashlib
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
PROMPT_FILE_EXTENSION = ".md"
# 12 hex characters (48 bits): short enough to read, far from colliding across versions.
FINGERPRINT_LENGTH = 12


class PromptNotFoundError(Exception):
    """Raised when there is no prompt file with the requested name."""


def load_prompt(prompt_name: str, prompts_dir: Path = PROMPTS_DIR) -> str:
    prompt_file = prompts_dir / f"{prompt_name}{PROMPT_FILE_EXTENSION}"
    if not prompt_file.is_file():
        raise PromptNotFoundError(f"prompt file not found: {prompt_file}")
    return prompt_file.read_text(encoding="utf-8").strip()


def prompt_versions(prompts_dir: Path = PROMPTS_DIR) -> dict[str, str]:
    """A short fingerprint of each prompt file, by prompt name. A fingerprint changes
    whenever its prompt changes, so a trace tells which version of each prompt produced
    it, and git keeps the text of every version. Line endings are ignored: the same
    prompt has the same fingerprint on Windows and Linux."""
    return {
        prompt_file.stem: _fingerprint(prompt_file.read_text(encoding="utf-8"))
        for prompt_file in sorted(prompts_dir.glob(f"*{PROMPT_FILE_EXTENSION}"))
    }


def prompts_version(versions: dict[str, str]) -> str:
    """One fingerprint for all the prompts together: it changes when any prompt changes."""
    return _fingerprint(
        "\n".join(f"{name}={version}" for name, version in sorted(versions.items()))
    )


def _fingerprint(text: str) -> str:
    normalized_text = text.replace("\r\n", "\n")
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()[:FINGERPRINT_LENGTH]
