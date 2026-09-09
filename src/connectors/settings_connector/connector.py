"""The façade the rest of the project holds.

``SettingsConnector`` is opened once for the life of the process, the same
way ``HollowConnector`` is, and is the only code that reads or writes the
settings file.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

from core import FEATURES, FeatureDescriptor

from .types import FeatureState, UnknownFeature

logger = logging.getLogger(__name__)


class SettingsConnector:
    """Read and write access to the persistent feature-toggle file."""

    def __init__(self, path: Path) -> None:
        """Open the connector on a settings file, reading it if it exists.

        Args:
            path: Where the settings file lives. Its parent directories are
                created when missing; the file itself is created on first write.
        """
        self._path = path
        self._lock = threading.Lock()
        self._enabled = self._read()
        logger.info("Settings opened at %s", self._path)

    def _read(self) -> dict[str, bool]:
        """The stored enabled-state of each feature, empty when there is none yet."""
        if not self._path.is_file():
            return {}
        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("Cannot read %s, starting from defaults: %s", self._path, error)
            return {}
        features = document.get("features", {})
        if not isinstance(features, dict):
            return {}
        return {
            str(feature_id): bool(enabled)
            for feature_id, enabled in features.items()
            if isinstance(enabled, bool)
        }

    def _write(self) -> None:
        """Persist the in-memory state, atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        document = {"features": self._enabled}
        tmp_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        tmp_path.write_text(json.dumps(document, indent=2), encoding="utf-8")
        os.replace(tmp_path, self._path)

    def _descriptor(self, feature_id: str) -> FeatureDescriptor:
        """The registry entry for a feature id.

        Raises:
            UnknownFeature: No entry of the registry carries this id.
        """
        for descriptor in FEATURES:
            if descriptor.id == feature_id:
                return descriptor
        raise UnknownFeature(f"No such feature: {feature_id}")

    def get_features(self) -> tuple[FeatureState, ...]:
        """Every registered feature, merged with its stored value."""
        with self._lock:
            return tuple(
                FeatureState(
                    id=descriptor.id,
                    label=descriptor.label,
                    description=descriptor.description,
                    enabled=self._enabled.get(descriptor.id, descriptor.default_enabled),
                )
                for descriptor in FEATURES
            )

    def set_feature(self, feature_id: str, enabled: bool) -> tuple[FeatureState, ...]:
        """Turn one feature on or off, and persist the change.

        Args:
            feature_id: The feature to change.
            enabled: The new state.

        Returns:
            Every registered feature, merged with its stored value, after the change.

        Raises:
            UnknownFeature: No entry of the registry carries this id.
        """
        with self._lock:
            self._descriptor(feature_id)
            self._enabled[feature_id] = enabled
            self._write()
        return self.get_features()
