"""Application settings, assembled once out of three layers.

The layers win in this order, each overruling the one before it:

1. the defaults written in this module, which is what a checkout with nothing
   configured runs on;
2. the YAML file at ``dragonglass.yml`` -- or wherever ``DRAGONGLASS_CONFIG_FILE``
   points -- which is where an installation writes down what it wants differently;
3. the environment, so a container passing its own values keeps them whatever
   the file says.

A missing file is not an error; a file that is present and unparseable is, and
the service refuses to start rather than run on settings nobody asked for. A
single value that cannot be read is reported and the layer below answers
instead.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Final

import yaml

logger = logging.getLogger(__name__)

ENV_PREFIX: Final = "DRAGONGLASS_"
CONFIG_FILE_ENV: Final = f"{ENV_PREFIX}CONFIG_FILE"
DEFAULT_CONFIG_FILE: Final = "dragonglass.yml"


class ConfigError(RuntimeError):
    """Raised when the configuration file exists but cannot be used."""


@dataclass(frozen=True, slots=True)
class PathsSettings:
    """Where the hollow and the built frontend are looked for."""

    hollow_root: Path = Path("data/root")
    frontend_dist: Path = Path("src/frontend/dist")
    settings_file: Path = Path("data/settings.json")
    tutor_file: Path = Path("data/tutor.json")


@dataclass(frozen=True, slots=True)
class ServerSettings:
    """How the HTTP service presents itself."""

    host: str = "127.0.0.1"
    port: int = 8017
    cors_origins: tuple[str, ...] = ()
    max_image_bytes: int = 10 * 1024 * 1024
    max_import_bytes: int = 50 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    """Level of the root logger."""

    level: str = "INFO"


@dataclass(frozen=True, slots=True)
class HollowSettings:
    """The conventions that turn a directory into a hollow."""

    note_extension: str = ".md"
    images_suffix: str = "_images"
    image_extensions: tuple[str, ...] = (
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".bmp",
    )
    sync_title: bool = True


@dataclass(frozen=True, slots=True)
class MarkdownSettings:
    """Which Markdown extensions are enabled, and which of ours are installed."""

    extensions: tuple[str, ...] = ("fenced_code", "tables", "toc", "sane_lists")
    wikilinks: bool = True
    image_paths: bool = True
    tasklists: bool = True


@dataclass(frozen=True, slots=True)
class Settings:
    """Every setting the application has, in one immutable object."""

    paths: PathsSettings = field(default_factory=PathsSettings)
    server: ServerSettings = field(default_factory=ServerSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    hollow: HollowSettings = field(default_factory=HollowSettings)
    markdown: MarkdownSettings = field(default_factory=MarkdownSettings)


def _read_file(path: Path) -> dict[str, Any]:
    """Return the parsed configuration file, or an empty mapping when absent.

    Raises:
        ConfigError: The file exists but is not readable YAML, or does not hold
            a mapping at its top level.
    """
    if not path.is_file():
        logger.debug("No configuration file at %s; using defaults", path)
        return {}
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ConfigError(f"Cannot read the configuration file {path}: {error}") from error
    if content is None:
        return {}
    if not isinstance(content, dict):
        raise ConfigError(f"The configuration file {path} must hold a mapping at its top level")
    return content


def _section(document: dict[str, Any], name: str) -> dict[str, Any]:
    """Return one top-level section of the document, empty when it is missing."""
    section = document.get(name)
    if section is None:
        return {}
    if not isinstance(section, dict):
        logger.warning("Section '%s' of the configuration is not a mapping; ignored", name)
        return {}
    return section


def _env(name: str) -> str | None:
    """Return the value of a ``DRAGONGLASS_`` variable, or None when unset or blank."""
    value = os.environ.get(f"{ENV_PREFIX}{name}")
    if value is None:
        return None
    value = value.strip()
    return value or None


def _pick(section: dict[str, Any], key: str, env_name: str) -> Any | None:
    """Return the raw value for one key, environment first, then the file."""
    from_env = _env(env_name)
    if from_env is not None:
        return from_env
    return section.get(key)


def _as_str(raw: Any) -> str:
    """Coerce a configured value to a stripped string."""
    text = str(raw).strip()
    if not text:
        raise ValueError("the value is empty")
    return text


def _as_int(raw: Any) -> int:
    """Coerce a configured value to an integer."""
    if isinstance(raw, bool):
        raise ValueError("a boolean is not a number")
    return int(str(raw).strip())


def _as_bool(raw: Any) -> bool:
    """Coerce a configured value to a boolean, accepting the usual spellings."""
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"'{raw}' is not a boolean")


def _as_tuple(raw: Any) -> tuple[str, ...]:
    """Coerce a configured value to a tuple of strings.

    A YAML list is taken as it is; a string is split on commas, which is how the
    same setting is written in an environment variable.
    """
    if isinstance(raw, (list, tuple)):
        items = [str(item).strip() for item in raw]
    else:
        items = [item.strip() for item in str(raw).split(",")]
    return tuple(item for item in items if item)


def _as_extension(raw: Any) -> str:
    """Coerce a configured value to a file extension with its leading dot."""
    text = _as_str(raw).lower()
    return text if text.startswith(".") else f".{text}"


def _as_extensions(raw: Any) -> tuple[str, ...]:
    """Coerce a configured value to a tuple of file extensions."""
    return tuple(dict.fromkeys(_as_extension(item) for item in _as_tuple(raw)))


def _resolve[T](
    settings: T,
    section: dict[str, Any],
    fields: dict[str, tuple[str, Any]],
) -> T:
    """Return a copy of ``settings`` with every field the outer layers override.

    Args:
        settings: The defaults for the section.
        section: The section as read from the configuration file.
        fields: Field name mapped to its environment variable and its coercion.

    Returns:
        The section, with each value that could be read replaced. A value that
        cannot be coerced is logged and left at the layer below.
    """
    overrides: dict[str, Any] = {}
    for name, (env_name, coerce) in fields.items():
        raw = _pick(section, name, env_name)
        if raw is None:
            continue
        try:
            overrides[name] = coerce(raw)
        except (TypeError, ValueError) as error:
            logger.warning("Ignoring the configured value for '%s': %s", name, error)
    return replace(settings, **overrides) if overrides else settings


def load_settings(config_file: Path | None = None) -> Settings:
    """Assemble the settings out of the defaults, the file and the environment.

    Args:
        config_file: The file to read. Defaults to ``DRAGONGLASS_CONFIG_FILE``,
            and to ``dragonglass.yml`` in the working directory when that is
            unset.

    Returns:
        The settings the application runs on.

    Raises:
        ConfigError: The file is there and cannot be parsed.
    """
    path = config_file or Path(_env("CONFIG_FILE") or DEFAULT_CONFIG_FILE)
    document = _read_file(path)

    return Settings(
        paths=_resolve(
            PathsSettings(),
            _section(document, "paths"),
            {
                "hollow_root": ("HOLLOW_ROOT", lambda raw: Path(_as_str(raw))),
                "frontend_dist": ("FRONTEND_DIST", lambda raw: Path(_as_str(raw))),
                "settings_file": ("SETTINGS_FILE", lambda raw: Path(_as_str(raw))),
                "tutor_file": ("TUTOR_FILE", lambda raw: Path(_as_str(raw))),
            },
        ),
        server=_resolve(
            ServerSettings(),
            _section(document, "server"),
            {
                "host": ("HOST", _as_str),
                "port": ("PORT", _as_int),
                "cors_origins": ("CORS_ORIGINS", _as_tuple),
                "max_image_bytes": ("MAX_IMAGE_BYTES", _as_int),
                "max_import_bytes": ("MAX_IMPORT_BYTES", _as_int),
            },
        ),
        logging=_resolve(
            LoggingSettings(),
            _section(document, "logging"),
            {"level": ("LOG_LEVEL", lambda raw: _as_str(raw).upper())},
        ),
        hollow=_resolve(
            HollowSettings(),
            _section(document, "hollow"),
            {
                "note_extension": ("NOTE_EXTENSION", _as_extension),
                "images_suffix": ("IMAGES_SUFFIX", _as_str),
                "image_extensions": ("IMAGE_EXTENSIONS", _as_extensions),
                "sync_title": ("SYNC_TITLE", _as_bool),
            },
        ),
        markdown=_resolve(
            MarkdownSettings(),
            _section(document, "markdown"),
            {
                "extensions": ("MARKDOWN_EXTENSIONS", _as_tuple),
                "wikilinks": ("MARKDOWN_WIKILINKS", _as_bool),
                "image_paths": ("MARKDOWN_IMAGE_PATHS", _as_bool),
                "tasklists": ("MARKDOWN_TASKLISTS", _as_bool),
            },
        ),
    )


settings: Final[Settings] = load_settings()
