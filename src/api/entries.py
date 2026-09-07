"""The ``/entries`` resource: what a note and a folder can both have done to them.

Renaming, moving and deleting do not care which of the two they are acting on,
so they are one resource rather than two.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from .dependencies import Hollow
from .schemas import EntryMove, EntryOut, EntryRename

router = APIRouter(prefix="/entries", tags=["entries"])


@router.patch("/{path:path}", response_model=EntryOut, summary="Rename a note or a folder")
def rename_entry(path: str, payload: EntryRename, hollow: Hollow) -> EntryOut:
    """Rename an entry in place.

    A note takes its ``*_images/`` folder with it.

    Args:
        path: The hollow-relative path of the entry.
        payload: The new name. A note gets its extension appended when missing.
        hollow: The hollow connector.

    Returns:
        The path and the name the entry ended up with.
    """
    new_path = hollow.rename_entry(path, payload.name)
    return EntryOut(path=new_path, name=new_path.rsplit("/", 1)[-1])


@router.post("/{path:path}/move", response_model=EntryOut, summary="Move a note or a folder")
def move_entry(path: str, payload: EntryMove, hollow: Hollow) -> EntryOut:
    """Move an entry into another folder.

    Args:
        path: The hollow-relative path of the entry.
        payload: The folder to move it into. An empty parent is the root.
        hollow: The hollow connector.

    Returns:
        The path and the name the entry ended up with.
    """
    new_path = hollow.move_entry(path, payload.parent)
    return EntryOut(path=new_path, name=new_path.rsplit("/", 1)[-1])


@router.delete(
    "/{path:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a note or a folder",
)
def delete_entry(path: str, hollow: Hollow) -> Response:
    """Delete a note, or a folder and everything under it.

    A note takes its ``*_images/`` folder with it. There is no bin.

    Args:
        path: The hollow-relative path of the entry.
        hollow: The hollow connector.

    Returns:
        An empty response.
    """
    hollow.delete_entry(path)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
