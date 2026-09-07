"""The ``/folders`` resource: making a folder in the hollow."""

from __future__ import annotations

from fastapi import APIRouter, status

from .dependencies import Hollow
from .schemas import EntryOut, FolderCreate

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post(
    "",
    response_model=EntryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a folder",
)
def create_folder(payload: FolderCreate, hollow: Hollow) -> EntryOut:
    """Create a folder inside the hollow.

    Args:
        payload: The parent folder and the name of the new one.
        hollow: The hollow connector.

    Returns:
        The path and the name of the folder that was created.
    """
    path = hollow.create_folder(payload.parent, payload.name)
    return EntryOut(path=path, name=path.rsplit("/", 1)[-1])
