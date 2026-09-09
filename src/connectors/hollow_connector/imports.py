"""Bringing notes and images into the hollow from an upload.

A ``.md`` file is written as a single note. A ``.zip`` is unpacked: every entry
that is a note or an image, by the hollow's own conventions, is written under
the chosen folder at its path inside the archive; everything else in it is
discarded rather than written to disk. Path traversal is refused the same way
it is everywhere else in the hollow: every target goes through
``PathResolver.resolve`` before anything is written.
"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path, PurePosixPath

from .images import unique_name
from .paths import PathResolver, check_name
from .types import ImportResult, InvalidName, InvalidPath, HollowConfig, HollowError

logger = logging.getLogger(__name__)

MAX_ENTRIES = 10_000
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024


def run(
    resolver: PathResolver,
    config: HollowConfig,
    parent: str,
    filename: str,
    content: bytes,
) -> ImportResult:
    """Import an upload into a folder of the hollow.

    Args:
        resolver: The path resolver opened on the hollow.
        config: The hollow conventions.
        parent: The hollow-relative folder to import into. Empty is the root.
        filename: The name the upload arrived with.
        content: The bytes of the upload.

    Returns:
        The paths that were written, and how many archive entries were left out.

    Raises:
        EntryNotFound: ``parent`` is not a folder of the hollow.
        InvalidName: The upload is neither a note, an image, nor a ``.zip``
            archive, or the archive is not a valid zip, or it is larger than
            this hollow accepts, unpacked.
        HollowError: A file could not be written.
    """
    folder = resolver.require_directory(parent)
    if filename.lower().endswith(".zip"):
        return _import_zip(resolver, config, parent, content)
    if config.is_note(filename):
        return _import_single(folder, resolver, filename, content)
    raise InvalidName(f"'{filename}' is neither a Markdown note nor a .zip archive")


def _import_single(
    folder: Path, resolver: PathResolver, filename: str, content: bytes
) -> ImportResult:
    """Write one uploaded note into ``folder``, without overwriting what is there."""
    name = unique_name(folder, check_name(PurePosixPath(filename).name))
    path = folder / name
    try:
        path.write_bytes(content)
    except OSError as error:
        raise HollowError(f"Cannot write '{name}': {error}") from error
    return ImportResult(created=(resolver.relative(path),))


def _import_zip(
    resolver: PathResolver, config: HollowConfig, parent: str, content: bytes
) -> ImportResult:
    """Unpack a ``.zip``, keeping only the entries that are notes or images."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as error:
        raise InvalidName(f"That is not a valid .zip archive: {error}") from error

    with archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) > MAX_ENTRIES:
            raise InvalidName(f"The archive holds more than {MAX_ENTRIES} files")
        if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
            raise InvalidName("The archive is larger, unpacked, than this hollow accepts")

        created: list[str] = []
        skipped = 0
        for info in infos:
            written = _import_entry(resolver, config, parent, archive, info)
            if written:
                created.append(written)
            else:
                skipped += 1

    return ImportResult(created=tuple(created), skipped=skipped)


def _import_entry(
    resolver: PathResolver,
    config: HollowConfig,
    parent: str,
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
) -> str | None:
    """Write one archive entry if it is a note or an image, and report where.

    Returns None -- rather than raising -- for anything that is not kept: an
    entry of the wrong kind, one whose path would leave the hollow, or one that
    the filesystem refuses. The whole import only fails when nothing in the
    archive could be trusted at all; one bad entry does not undo the rest.
    """
    member = PurePosixPath(info.filename)
    name = member.name
    if not name or not (config.is_note(name) or config.is_image(name)):
        return None

    relative_dir = member.parent.as_posix()
    target_parent = resolver.join(parent, relative_dir) if relative_dir != "." else parent
    try:
        target_folder = resolver.resolve(target_parent)
        target_folder.mkdir(parents=True, exist_ok=True)
        target_name = unique_name(target_folder, name)
        (target_folder / target_name).write_bytes(archive.read(info))
    except (InvalidPath, OSError) as error:
        logger.warning("Skipping '%s' of the archive: %s", info.filename, error)
        return None
    return resolver.relative(target_folder / target_name)
