"""The only code in the project that reads or writes the settings file.

``SettingsConnector`` is the whole surface; everything else here is what
stands behind it.
"""

from .connector import SettingsConnector
from .types import FeatureState, UnknownFeature

__all__ = [
    "FeatureState",
    "SettingsConnector",
    "UnknownFeature",
]
