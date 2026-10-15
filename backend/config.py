from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text("utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()


@dataclass(frozen=True)
class Settings:
    api_key: str = os.getenv("AI_API_KEY", "")
    base_url: str = os.getenv("AI_BASE_URL", "https://aiapi.market/v1")
    model: str = os.getenv("AI_MODEL", "")
    image_model: str = os.getenv("AI_IMAGE_MODEL", "")
    llm_timeout: float = float(os.getenv("AI_LLM_TIMEOUT", "90"))
    host: str = os.getenv("APP_HOST", "127.0.0.1")
    port: int = int(os.getenv("APP_PORT", "4098"))
    data_dir: Path = ROOT / "data"

    @property
    def llm_ready(self) -> bool:
        return bool(self.api_key and self.model)


settings = Settings()
for folder in (settings.data_dir, settings.data_dir / "uploads", settings.data_dir / "artifacts"):
    folder.mkdir(parents=True, exist_ok=True)
