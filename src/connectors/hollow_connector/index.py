"""The flat index of every note in the hollow.

This is what a ``[[wiki-link]]`` is resolved against: a name, the folder holding
it, and the path to open. It is rebuilt on demand rather than cached, because
the hollow is a directory anything else may also be writing to.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .paths import PathResolver
from .types import IndexedNote, NoteIndex, HollowConfig

logger = logging.getLogger(__name__)


def build(resolver: PathResolver, config: HollowConfig) -> NoteIndex:
    """Walk the whole hollow and index every note in it.

    Args:
        resolver: The path resolver opened on the hollow.
        config: The conventions saying which file is a note.

    Returns:
        Every note of the hollow, sorted by path. A folder that cannot be read is
        logged and skipped rather than failing the whole index.
    """
    notes: list[IndexedNote] = []
    for path in _walk(resolver.root):
        if not config.is_note(path.name):
            continue
        relative = resolver.relative(path)
        notes.append(
            IndexedNote(
                name=config.stem(path.name),
                folder=resolver.parent_of(relative),
                path=relative,
            )
        )
    notes.sort(key=lambda note: note.path.lower())
    return NoteIndex(notes=tuple(notes))


def _walk(directory: Path) -> list[Path]:
    """Every file below a directory, skipping hidden folders and unreadable ones."""
    found: list[Path] = []
    try:
        entries = sorted(directory.iterdir(), key=lambda item: item.name.lower())
    except OSError as error:
        logger.warning("Skipping %s while indexing: %s", directory, error)
        return found

    for entry in entries:
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            found.extend(_walk(entry))
        elif entry.is_file():
            found.append(entry)
    return found
