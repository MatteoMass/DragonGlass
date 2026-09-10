"""Where a quiz set's images live: one folder per quiz, named after its id.

Kept separate from ``connectors.hollow_connector.images`` on purpose -- the
tutor connector knows nothing about the hollow, quiz images are not a note's
sidecar, and each connector owns its own corner of the filesystem.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .types import InvalidImage

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_REPEATED_DASH = re.compile(r"-{2,}")

IMAGE_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp")


def is_image(name: str) -> bool:
    """Whether a file name has an extension the tutor accepts as an image."""
    lowered = name.lower()
    return any(lowered.endswith(extension) for extension in IMAGE_EXTENSIONS)


def sanitise_name(name: str, *, fallback: str = "image") -> str:
    """Reduce an uploaded file name to something safe to write to disk.

    Accents are folded, spaces and anything unusual become dashes, and the
    extension is kept and lowered. A name that survives as nothing at all
    falls back to ``fallback``.
    """
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    plain = plain.strip().replace(" ", "-")
    stem, dot, extension = plain.rpartition(".")
    if not dot:
        stem, extension = plain, ""
    stem = _REPEATED_DASH.sub("-", _UNSAFE.sub("-", stem)).strip("-._")
    extension = _UNSAFE.sub("", extension).lower()
    if not stem:
        stem = fallback
    return f"{stem}.{extension}" if extension else stem


def unique_name(folder: Path, name: str) -> str:
    """Return a name free in ``folder``, suffixing ``-1``, ``-2``... as needed.

    An upload never overwrites what is already there.
    """
    if not (folder / name).exists():
        return name
    stem, dot, extension = name.rpartition(".")
    if not dot:
        stem, extension = name, ""
    suffix = f".{extension}" if extension else ""
    for counter in range(1, 10_000):
        candidate = f"{stem}-{counter}{suffix}"
        if not (folder / candidate).exists():
            return candidate
    raise InvalidImage(f"No free name is left for '{name}'")


def store(root: Path, quiz_id: str, filename: str, content: bytes) -> str:
    """Write an uploaded image into a quiz set's own image folder.

    Args:
        root: Where every quiz set's images are kept, one folder per quiz.
        quiz_id: The quiz set the image belongs to.
        filename: The name the upload arrived with.
        content: The bytes of the image.

    Returns:
        The tutor-relative path it was stored at (``"<quiz_id>/<name>"``).

    Raises:
        InvalidImage: The name is not one the tutor accepts as an image, or
            nothing usable is left of it once sanitised.
    """
    if not is_image(filename):
        raise InvalidImage(f"'{filename}' is not an image the tutor accepts")
    name = sanitise_name(filename)
    if not is_image(name):
        raise InvalidImage(f"'{filename}' is not an image the tutor accepts")
    folder = root / quiz_id
    folder.mkdir(parents=True, exist_ok=True)
    name = unique_name(folder, name)
    (folder / name).write_bytes(content)
    return f"{quiz_id}/{name}"
