"""What the settings connector hands out, and what it raises."""

from __future__ import annotations

from dataclasses import dataclass


class UnknownFeature(Exception):
    """No entry of the feature registry carries the requested id."""


@dataclass(frozen=True, slots=True)
class FeatureState:
    """One feature merged with its stored value.

    Attributes:
        id: The feature's stable identifier.
        label: The name shown in the settings panel.
        description: The sentence shown under the label.
        enabled: Whether it is currently on.
    """

    id: str
    label: str
    description: str
    enabled: bool
