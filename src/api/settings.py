"""The ``/settings`` resource: which native features are turned on."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from connectors.settings_connector import UnknownFeature

from .dependencies_settings import SettingsStore
from .schemas_settings import FeatureOut, FeatureUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=list[FeatureOut], summary="List every togglable feature")
def list_features(store: SettingsStore) -> list[FeatureOut]:
    """Every registered feature, with its current state.

    Args:
        store: The settings connector.

    Returns:
        One entry per feature in the registry.
    """
    return [FeatureOut.model_validate(feature) for feature in store.get_features()]


@router.patch("/{feature_id}", response_model=list[FeatureOut], summary="Turn a feature on or off")
def set_feature(feature_id: str, payload: FeatureUpdate, store: SettingsStore) -> list[FeatureOut]:
    """Turn one feature on or off.

    Args:
        feature_id: The feature to change.
        payload: The new state.
        store: The settings connector.

    Returns:
        Every registered feature, with its state after the change.

    Raises:
        HTTPException: 404 when no feature carries this id.
    """
    try:
        features = store.set_feature(feature_id, payload.enabled)
    except UnknownFeature as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return [FeatureOut.model_validate(feature) for feature in features]
