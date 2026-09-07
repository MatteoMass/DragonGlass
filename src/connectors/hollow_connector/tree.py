"""Walking the hollow into ``Entry`` nodes.

Folders, notes and images are shown; anything else on disk is ignored rather
than hidden -- it is simply not the application's business, and it stays where
it is.
"""

from __future__ import annotations

from pathlib import Path

from .paths import PathResolver
from .types import Entry, EntryKind, HollowConfig


def _sort_key(entry: Entry) -> tuple[int, str]:
    """Order folders before files, then by name, case-insensitively."""
    return (0 if entry.kind is EntryKind.FOLDER else 1, entry.name.lower())


def _is_hidden(name: str) -> bool:
    """Whether a name is one the tree leaves alone -- dotfiles and the like."""
    return name.startswith(".")


def walk(resolver: PathResolver, config: HollowConfig, relative: str = "") -> tuple[Entry, ...]:
    """Walk a folder of the hollow into the nodes below it.

    Args:
        resolver: The path resolver opened on the hollow.
        config: The conventions telling a note and an image apart.
        relative: The hollow-relative folder to walk. Empty is the root.

    Returns:
        The children of the folder, folders first and then files, each sorted by
        name. Folders carry their own children; notes and images do not.

    Raises:
        EntryNotFound: The folder is not in the hollow.
        InvalidPath: The path would leave the hollow.
    """
    directory = resolver.require_directory(relative)
    return _children(resolver, config, directory)


def _children(resolver: PathResolver, config: HollowConfig, directory: Path) -> tuple[Entry, ...]:
    """Build the nodes directly below one directory, recursing into folders."""
    entries: list[Entry] = []
    try:
        candidates = sorted(directory.iterdir(), key=lambda item: item.name.lower())
    except OSError:
        return ()

    for item in candidates:
        name = item.name
        if _is_hidden(name):
            continue
        path = resolver.relative(item)
        if item.is_dir():
            entries.append(
                Entry(
                    kind=EntryKind.FOLDER,
                    name=name,
                    path=path,
                    children=_children(resolver, config, item),
                )
            )
        elif item.is_file():
            if config.is_note(name):
                entries.append(Entry(kind=EntryKind.NOTE, name=name, path=path))
            elif config.is_image(name):
                entries.append(Entry(kind=EntryKind.IMAGE, name=name, path=path))

    return tuple(sorted(entries, key=_sort_key))
