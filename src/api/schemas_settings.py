"""The payloads the ``/settings`` resource takes and gives back, and nothing else."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FeatureOut(BaseModel):
    """A togglable feature, with its current state."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="The feature's stable identifier.")
    label: str = Field(description="The name shown in the settings panel.")
    description: str = Field(description="The sentence shown under the label.")
    enabled: bool = Field(description="Whether it is currently on.")


class FeatureUpdate(BaseModel):
    """The body of a toggle."""

    enabled: bool = Field(description="The new state of the feature.")
