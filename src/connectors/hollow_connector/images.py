"""The ``<note>_images/`` sidecars.

Upload, name sanitising and de-duplication, and following the note they belong
to on every rename, move and delete. A note's images live beside it, in a folder
named after it, so that moving the note is enough to move its pictures.
"""

from __future__ import annotations

import logging
import re
import shutil
import unicodedata
from pathlib import Path

from .paths import PathResolver
from .types import EntryAlreadyExists, InvalidName, UploadedImage, HollowConfig, HollowError

logger = logging.getLogger(__name__)

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_REPEATED_DASH = re.compile(r"-{2,}")


def sanitise_name(name: str, *, fallback: str = "image") -> str:
    """Reduce an uploaded file name to something safe to write to disk.

    Accents are folded, spaces and anything unusual become dashes, and the
    extension is kept and lowered. A name that survives as nothing at all falls
    back to ``fallback``.

    Args:
        name: The name as the browser sent it.
        fallback: The stem to use when nothing usable is left.

    Returns:
        A file name made only of letters, digits, dots, dashes and underscores.
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

    An upload never overwrites what is already there: ``foto.png`` becomes
    ``foto-1.png`` when the first one is taken.
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
    raise EntryAlreadyExists(f"No free name is left for '{name}'")


def folder_for(resolver: PathResolver, config: HollowConfig, note_path: str) -> Path:
    """The absolute path of the sidecar folder belonging to a note.

    The folder need not exist; this only says where it would be.
    """
    parent = resolver.parent_of(note_path)
    name = config.images_folder_name(resolver.name_of(note_path))
    return resolver.resolve(resolver.join(parent, name))


def relative_folder_for(resolver: PathResolver, config: HollowConfig, note_path: str) -> str:
    """The hollow-relative path of the sidecar folder belonging to a note."""
    parent = resolver.parent_of(note_path)
    return resolver.join(parent, config.images_folder_name(resolver.name_of(note_path)))


def store(
    resolver: PathResolver,
    config: HollowConfig,
    note_path: str,
    filename: str,
    content: bytes,
) -> UploadedImage:
    """Write an uploaded image into a note's sidecar folder.

    The folder is created when it is not there. The name is sanitised and then
    de-duplicated, so an upload never overwrites an existing file.

    Args:
        resolver: The path resolver opened on the hollow.
        config: The hollow conventions.
        note_path: The hollow-relative path of the note the image belongs to.
        filename: The name the file arrived with.
        content: The bytes of the image.

    Returns:
        The name the file was given and its hollow-relative path.

    Raises:
        InvalidName: Nothing usable is left of the name, or its extension is not
            one the hollow treats as an image.
        HollowError: The bytes could not be written.
    """
    name = sanitise_name(filename)
    if not config.is_image(name):
        raise InvalidName(f"'{filename}' is not an image the hollow accepts")

    folder = folder_for(resolver, config, note_path)
    folder.mkdir(parents=True, exist_ok=True)
    name = unique_name(folder, name)
    try:
        (folder / name).write_bytes(content)
    except OSError as error:
        raise HollowError(f"Cannot write the image '{name}': {error}") from error

    return UploadedImage(name=name, path=resolver.relative(folder / name))


def follow(
    resolver: PathResolver,
    config: HollowConfig,
    old_note_path: str,
    new_note_path: str,
) -> str | None:
    """Move a note's sidecar folder to where the note has just gone.

    Args:
        resolver: The path resolver opened on the hollow.
        config: The hollow conventions.
        old_note_path: Where the note used to be.
        new_note_path: Where the note is now.

    Returns:
        The new hollow-relative path of the sidecar folder, or None when the note
        had no images or the folder could not follow it.
    """
    source = folder_for(resolver, config, old_note_path)
    if not source.is_dir():
        return None
    destination = folder_for(resolver, config, new_note_path)
    if source == destination:
        return resolver.relative(source)
    if destination.exists():
        logger.warning("Not moving %s: %s is already taken", source, destination)
        return None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
    except OSError as error:
        logger.warning("The images of '%s' could not follow it: %s", old_note_path, error)
        return None
    return resolver.relative(destination)


def discard(resolver: PathResolver, config: HollowConfig, note_path: str) -> None:
    """Delete a note's sidecar folder, if it has one.

    A folder that cannot be removed is logged rather than raised: the note it
    belonged to is already gone, and failing here would report the deletion as
    unsuccessful when it was not.
    """
    folder = folder_for(resolver, config, note_path)
    if not folder.is_dir():
        return
    try:
        shutil.rmtree(folder)
    except OSError as error:
        logger.warning("The images of '%s' could not be removed: %s", note_path, error)
