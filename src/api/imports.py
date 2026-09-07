"""The ``/imports`` resource: bringing notes and images into the hollow from an upload."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from connectors.hollow_connector import InvalidName

from .dependencies import Hollow
from .schemas import ImportOut

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post(
    "",
    response_model=ImportOut,
    status_code=status.HTTP_201_CREATED,
    summary="Import a note, or unpack a .zip of notes and images",
)
async def import_upload(
    request: Request,
    hollow: Hollow,
    parent: str = Form(default="", description="The folder to import into. Empty is the root."),
    file: UploadFile = File(description="A .md note, or a .zip archive to unpack."),
) -> ImportOut:
    """Bring a Markdown note, or the notes and images of a ``.zip``, into the hollow.

    A ``.zip`` is unpacked: every entry that is a note or an image, by the
    hollow's own conventions, is written under ``parent`` at its path inside the
    archive; anything else in it is discarded rather than written to disk. A
    ``.md`` file is written as a single note. Nothing else is accepted.

    Args:
        request: The request, read for the configured size limit.
        hollow: The hollow connector.
        parent: The hollow-relative folder to import into. Empty is the root.
        file: The uploaded file, sent as ``multipart/form-data``.

    Returns:
        The paths that were written, and how many entries of an archive were
        neither a note nor an image and so were left out.

    Raises:
        HTTPException: The upload is empty or larger than the configured limit.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty")

    limit = request.app.state.max_import_bytes
    if len(content) > limit:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"The upload is larger than the {limit} bytes this hollow accepts",
        )

    if not file.filename:
        raise InvalidName("The uploaded file has no name")

    result = hollow.import_upload(parent, file.filename, content)
    return ImportOut(created=list(result.created), skipped=result.skipped)
