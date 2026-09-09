"""What the tutor's own router asks for."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from connectors.tutor_connector import TutorConnector


def get_tutor_store(request: Request) -> TutorConnector:
    """The tutor connector opened for the life of the process."""
    return request.app.state.tutor_store


TutorStore = Annotated[TutorConnector, Depends(get_tutor_store)]
