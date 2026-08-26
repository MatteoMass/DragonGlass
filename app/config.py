from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config.yaml"

SUPPORTED_MODES = ("local", "docker")


@dataclass(frozen=True)
class StorageConfig:
    mode: str
    root: Path


def load_storage_config(config_path: Path = DEFAULT_CONFIG_PATH) -> StorageConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    storage = data.get("storage", {})
    mode = storage.get("mode", "local")

    if mode not in SUPPORTED_MODES:
        raise ValueError(
            f"Modalita' di persistenza non supportata: '{mode}'. "
            f"Valori ammessi: {SUPPORTED_MODES}"
        )

    mode_config = storage.get(mode, {})
    root_value = mode_config.get("root")
    if not root_value:
        raise ValueError(
            f"Percorso 'root' mancante per la modalita' '{mode}' in {config_path}"
        )

    root_path = Path(root_value)
    if not root_path.is_absolute():
        root_path = BASE_DIR / root_path

    return StorageConfig(mode=mode, root=root_path)
