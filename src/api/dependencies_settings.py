"""What the settings resource asks for, plus the gate any plugin router uses.

``require_feature`` lives here rather than in the hollow's own dependencies:
it is the settings plugin's contribution to the rest of the API, the one
piece another plugin's router needs to gate itself behind a toggle.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from connectors.settings_connector import SettingsConnector


def get_settings_store(request: Request) -> SettingsConnector:
    """The settings connector opened for the life of the process."""
    return request.app.state.settings_store


SettingsStore = Annotated[SettingsConnector, Depends(get_settings_store)]


def require_feature(feature_id: str) -> Callable[[SettingsStore], None]:
    """Build a dependency that 404s unless the named feature is turned on.

    The state is read fresh from the settings store on every request, so a
    router gated by this needs no conditional registration at startup:
    toggling the feature takes effect immediately, without a restart.
    """

    def check(store: SettingsStore) -> None:
        for feature in store.get_features():
            if feature.id == feature_id:
                if feature.enabled:
                    return
                break
        raise HTTPException(status_code=404, detail=f"'{feature_id}' is not enabled")

    return check
