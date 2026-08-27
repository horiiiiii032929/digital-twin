"""Validated runtime configuration for demo, test, and staging modes."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[3]


class RuntimeMode(StrEnum):
    DEMO = "demo"
    TEST = "test"
    STAGING = "staging"


class GeneratorMode(StrEnum):
    DETERMINISTIC = "deterministic"
    DEEPSEEK_V4_FLASH = "deepseek-v4-flash"
    OPENAI_GPT_5_4_MINI = "openai-gpt-5.4-mini"


class StudentTutoringMode(StrEnum):
    GROUNDED_ASSISTANT = "grounded-assistant"
    BOUNDED_TUTORING_GRAPH = "bounded-tutoring-graph"


@dataclass(frozen=True, slots=True)
class AppSettings:
    mode: RuntimeMode = RuntimeMode.DEMO
    database_path: Path = ROOT / "data/interim/runtime/digital-twin.sqlite3"
    data_root: Path = ROOT / "data/interim/runtime"
    allowed_origins: tuple[str, ...] = ("http://localhost:5173",)
    session_cookie_name: str = "digital_twin_session"
    session_ttl_seconds: int = 8 * 60 * 60
    secure_cookies: bool = False
    max_upload_bytes: int = 50 * 1024 * 1024
    max_object_store_bytes: int = 5 * 1024 * 1024 * 1024
    login_attempts_per_minute: int = 10
    authenticated_requests_per_minute: int = 120
    log_level: str = "INFO"
    generator_mode: GeneratorMode = GeneratorMode.DETERMINISTIC
    student_profile_path: Path = (
        ROOT
        / "research/05_evaluation/profiles/student-tutor-v1.json"
    )
    student_tutoring_mode: StudentTutoringMode = (
        StudentTutoringMode.GROUNDED_ASSISTANT
    )
    proactive_outreach_worker_enabled: bool = False
    provider_max_calls_per_process: int = 1_000
    provider_cost_cap_usd: float = 5.0

    @classmethod
    def from_env(cls) -> "AppSettings":
        mode = RuntimeMode(os.getenv("APP_MODE", RuntimeMode.DEMO.value))
        default_root = ROOT / "data/interim/runtime"
        data_root = Path(os.getenv("APP_DATA_ROOT", str(default_root))).expanduser()
        database_path = Path(
            os.getenv("APP_DATABASE_PATH", str(data_root / "digital-twin.sqlite3"))
        ).expanduser()
        origins_value = os.getenv("APP_ALLOWED_ORIGINS", "http://localhost:5173")
        origins = tuple(
            origin.strip().rstrip("/")
            for origin in origins_value.split(",")
            if origin.strip()
        )
        settings = cls(
            mode=mode,
            database_path=database_path,
            data_root=data_root,
            allowed_origins=origins,
            session_cookie_name=os.getenv(
                "APP_SESSION_COOKIE_NAME", "digital_twin_session"
            ).strip(),
            session_ttl_seconds=_positive_int("APP_SESSION_TTL_SECONDS", 8 * 60 * 60),
            secure_cookies=_boolean(
                "APP_SECURE_COOKIES", default=mode == RuntimeMode.STAGING
            ),
            max_upload_bytes=_positive_int("APP_MAX_UPLOAD_BYTES", 50 * 1024 * 1024),
            max_object_store_bytes=_positive_int(
                "APP_MAX_OBJECT_STORE_BYTES", 5 * 1024 * 1024 * 1024
            ),
            login_attempts_per_minute=_positive_int(
                "APP_LOGIN_ATTEMPTS_PER_MINUTE", 10
            ),
            authenticated_requests_per_minute=_positive_int(
                "APP_AUTHENTICATED_REQUESTS_PER_MINUTE", 120
            ),
            log_level=os.getenv("APP_LOG_LEVEL", "INFO").upper(),
            generator_mode=GeneratorMode(
                os.getenv("APP_GENERATOR_MODE", GeneratorMode.DETERMINISTIC.value)
            ),
            student_profile_path=_repository_path(
                os.getenv(
                    "APP_STUDENT_PROFILE_PATH",
                    str(
                        ROOT
                        / "research/05_evaluation/profiles/student-tutor-v1.json"
                    ),
                )
            ),
            student_tutoring_mode=StudentTutoringMode(
                os.getenv(
                    "APP_STUDENT_TUTORING_MODE",
                    StudentTutoringMode.GROUNDED_ASSISTANT.value,
                )
            ),
            proactive_outreach_worker_enabled=_boolean(
                "APP_PROACTIVE_OUTREACH_WORKER_ENABLED", default=False
            ),
            provider_max_calls_per_process=_positive_int(
                "APP_PROVIDER_MAX_CALLS_PER_PROCESS", 1_000
            ),
            provider_cost_cap_usd=_positive_float("APP_PROVIDER_COST_CAP_USD", 5.0),
        )
        settings.validate()
        return settings

    @property
    def credential_auth_enabled(self) -> bool:
        return self.mode == RuntimeMode.STAGING

    @property
    def database_directory(self) -> Path:
        return self.database_path.parent

    @property
    def object_root(self) -> Path:
        return self.data_root / "objects"

    @property
    def region_crop_root(self) -> Path:
        return self.data_root / "derived/region-crops"

    @property
    def source_root(self) -> Path:
        return self.data_root / "derived/course-sources"

    def validate(self) -> None:
        if (
            not self.session_cookie_name
            or self.session_cookie_name.strip() != self.session_cookie_name
            or any(character in self.session_cookie_name for character in ";,\r\n\t ")
        ):
            raise ValueError("APP_SESSION_COOKIE_NAME cannot be empty")
        if not self.allowed_origins:
            raise ValueError("APP_ALLOWED_ORIGINS requires at least one origin")
        if len(self.allowed_origins) != len(set(self.allowed_origins)):
            raise ValueError("duplicate CORS origins are not permitted")
        for origin in self.allowed_origins:
            parsed = urlsplit(origin)
            if (
                "*" in origin
                or parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS origins must be plain HTTP(S) origins")
        integer_limits = {
            "APP_SESSION_TTL_SECONDS": self.session_ttl_seconds,
            "APP_MAX_UPLOAD_BYTES": self.max_upload_bytes,
            "APP_MAX_OBJECT_STORE_BYTES": self.max_object_store_bytes,
            "APP_LOGIN_ATTEMPTS_PER_MINUTE": self.login_attempts_per_minute,
            "APP_AUTHENTICATED_REQUESTS_PER_MINUTE": (
                self.authenticated_requests_per_minute
            ),
            "APP_PROVIDER_MAX_CALLS_PER_PROCESS": (self.provider_max_calls_per_process),
        }
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in integer_limits.values()
        ):
            raise ValueError("runtime integer limits must be positive integers")
        if (
            isinstance(self.provider_cost_cap_usd, bool)
            or not math.isfinite(self.provider_cost_cap_usd)
            or self.provider_cost_cap_usd <= 0
        ):
            raise ValueError("APP_PROVIDER_COST_CAP_USD must be positive")
        if self.mode == RuntimeMode.STAGING:
            if (
                self.student_tutoring_mode
                == StudentTutoringMode.BOUNDED_TUTORING_GRAPH
            ):
                raise ValueError(
                    "bounded tutoring graph is not yet selected for staging release"
                )
            if not self.secure_cookies:
                raise ValueError("staging requires APP_SECURE_COOKIES=true")
            if any(
                not origin.startswith("https://") for origin in self.allowed_origins
            ):
                raise ValueError("staging origins must use https://")
            if str(self.database_path) == ":memory:":
                raise ValueError("staging requires a durable database path")
            if not self.database_path.is_absolute() or not self.data_root.is_absolute():
                raise ValueError("staging database and data paths must be absolute")
            if self.max_upload_bytes > 64 * 1024 * 1024:
                raise ValueError(
                    "staging APP_MAX_UPLOAD_BYTES cannot exceed the proxy 64 MiB cap"
                )
        if self.generator_mode == GeneratorMode.DEEPSEEK_V4_FLASH:
            raise ValueError(
                "APP_GENERATOR_MODE=deepseek-v4-flash is historical and cannot "
                "be selected by the prospective R1 runtime"
            )
        if (
            self.generator_mode == GeneratorMode.OPENAI_GPT_5_4_MINI
            and not os.getenv("OPENAI_API_KEY", "").strip()
        ):
            raise ValueError(
                "OPENAI_API_KEY is required when "
                "APP_GENERATOR_MODE=openai-gpt-5.4-mini"
            )
        if not self.student_profile_path.is_file():
            raise ValueError("APP_STUDENT_PROFILE_PATH must identify a profile file")


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    value = default if raw is None else int(raw)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _boolean(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    value = default if raw is None else float(raw)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _repository_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path
