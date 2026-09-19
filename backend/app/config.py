"""Runtime configuration. Everything is local-first and deny-by-default."""

from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Smart Utility Backend"
    host: str = "127.0.0.1"
    port: int = 8000
    # NoDecode on every list field: without it pydantic-settings JSON-decodes
    # the raw env value before validators run, so a plain
    # "CORS_ORIGINS=http://a,http://b" dies in the source layer and _split_csv
    # below never gets a chance to split it. The .env file is written for a
    # human to edit, and a human writes a comma-separated list.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    data_dir: Path = Path("./data")

    max_upload_bytes: int = 10 * 1024 * 1024

    # --- OCR ---
    ocr_engine: str = "tesseract"
    ocr_languages: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["eng", "hin", "mar"]
    )
    ocr_dpi: int = 300
    ocr_max_pages: int = 12
    ocr_timeout_seconds: int = 180
    ocr_keep_page_images: bool = False
    ocr_min_confidence: float = 40.0
    # A reading below this is retried with the full language set. Separate from
    # ``ocr_min_confidence`` on purpose: that one decides whether a result is
    # good enough to show the user, this one decides whether a second pass is
    # worth the time. A confident Latin page scores above 90 and skips it; a
    # page carrying Devanagari read with ``eng`` alone scores in the 60s-70s
    # and gets a second look.
    ocr_widen_below: float = 85.0

    # --- language ---
    enable_translation: bool = False

    # --- agent ---
    agent_enabled: bool = False
    agent_cli_path: str = ""
    agent_timeout_seconds: int = 90
    agent_allowed_tools: str = ""
    agent_sandbox_dir: str = "agent_sandbox"
    # Environment variables forwarded to the agent process. Everything else is
    # dropped, so no ambient credential leaks into a subprocess. If your agent
    # authenticates via an env var, name it here explicitly.
    agent_env_allowlist: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # Which agent the pipeline calls. ``cli`` is the local subprocess above and
    # can only *choose between* candidate strings OCR already found. ``openrouter``
    # reads the OCR text itself, so it can recover fields the rules never
    # located — at the cost of document text leaving this machine.
    agent_provider: str = "openrouter"
    # Must be a model the account can actually be billed for: a key with no
    # credit gets HTTP 402 from every paid model, and the agent stage then
    # contributes nothing while still reporting a normal duration.
    agent_model: str = "deepseek/deepseek-v4-flash"
    agent_api_base: str = "https://openrouter.ai/api/v1"
    # Name of the environment variable holding the key. The key itself is never
    # written to a config file, never logged, and never echoed in /health.
    agent_api_key_env: str = "OPENROUTER_API_KEY"
    # Optional inline key. Prefer leaving this empty and exporting the variable
    # named above instead, so the key never sits in a file on disk.
    agent_api_key: str = ""
    agent_http_timeout_seconds: float = 60.0
    # Redact structured personal identifiers before any text is sent. See
    # app/core/redaction.py for exactly what this does and does not catch.
    agent_redact: bool = True
    agent_max_ocr_chars: int = 16_000

    # The assistant answers from the stored analysis. With this on it may also
    # read the OCR text to handle questions the templates do not cover. Numeric
    # replies are still validated against the analysis before they are returned.
    assistant_model_enabled: bool = False

    # --- weather ---
    # Off by default. When enabled, the only thing sent off the machine is a
    # coordinate pair the operator configured — never anything read from a bill.
    # Coordinates rather than a place name, so no address ever leaves the host.
    weather_enabled: bool = False
    weather_api_base: str = "https://api.open-meteo.com/v1"
    weather_timeout_seconds: float = 6.0
    weather_latitude: float | None = None
    weather_longitude: float | None = None

    # --- logging ---
    log_level: str = "INFO"
    log_redact: bool = True
    log_dir: Path = Path("./data/logs")

    @field_validator("cors_origins", "ocr_languages", "agent_env_allowlist", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("data_dir", "log_dir", mode="after")
    @classmethod
    def _absolute(cls, value: Path) -> Path:
        value = Path(value).expanduser()
        return value if value.is_absolute() else (BACKEND_DIR / value).resolve()

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def results_dir(self) -> Path:
        return self.data_dir / "results"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "db" / "smart_utility.db"

    @property
    def agent_sandbox_path(self) -> Path:
        return self.data_dir / self.agent_sandbox_dir

    def resolve_agent_key(self) -> str | None:
        """The agent's API key, from the environment or the config field.

        Read at call time rather than at import so a key exported after the
        process started is still picked up, and so the value is never held on
        the settings object where it could be repr'd into a log line.
        """
        from os import environ

        return environ.get(self.agent_api_key_env, "").strip() or self.agent_api_key.strip() or None

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.uploads_dir,
            self.processed_dir,
            self.results_dir,
            self.log_dir,
            self.db_path.parent,
            self.agent_sandbox_path,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def tesseract_available(self) -> bool:
        return shutil.which("tesseract") is not None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
