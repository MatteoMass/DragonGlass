"""The static catalogue of togglable features.

Adding a plugin means adding one entry here plus its own gated router and
frontend view; nothing else in the toggle mechanism changes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeatureDescriptor:
    """One feature the settings panel can turn on or off.

    Attributes:
        id: The stable identifier stored in the settings file and used in URLs.
        label: The name shown in the settings panel.
        description: The sentence shown under the label.
        default_enabled: What a feature not yet in the settings file answers as.
    """

    id: str
    label: str
    description: str
    default_enabled: bool = False


FEATURES: tuple[FeatureDescriptor, ...] = (
    FeatureDescriptor(
        id="tutor",
        label="DragonGlass Tutor",
        description="Study Q&A generated from your notes.",
    ),
)
