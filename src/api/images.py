"""The ``/images`` resource: putting a picture in a note's sidecar folder."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from connectors.hollow_connector import InvalidName

from .dependencies import Hollow
from .schemas import ImageOut

router = APIRouter(prefix="/images", tags=["images"])


@router.post(
    "/{path:path}",
    response_model=ImageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image for a note",
)
async def upload_image(
    path: str,
    request: Request,
    hollow: Hollow,
    image: UploadFile = File(description="The image file."),
) -> ImageOut:
    """Store an uploaded image in the ``<note>_images/`` folder beside a note.

    The name is sanitised and de-duplicated on the way in, so an upload never
    overwrites what is already there.

    Args:
        path: The hollow-relative path of the note the image belongs to.
        request: The request, read for the configured size limit.
        hollow: The hollow connector.
        image: The uploaded file, sent as ``multipart/form-data``.

    Returns:
        The name the file was given and its path, ready to be written into the
        Markdown.

    Raises:
        HTTPException: The upload is empty or larger than the configured limit.
    """
    hollow.read_note(path)

    content = await image.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded image is empty")

    limit = request.app.state.max_image_bytes
    if len(content) > limit:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"The image is larger than the {limit} bytes this hollow accepts",
        )

    if not image.filename:
        raise InvalidName("The uploaded file has no name")

    stored = hollow.store_image(path, image.filename, content)
    return ImageOut(name=stored.name, path=stored.path)
