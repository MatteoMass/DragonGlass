"""Reading and writing notes, and the moves that folders and notes share.

A note is a file; everything here is one of the few things that can happen to a
file, with the sidecar image folder taken along whenever the note moves.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from . import images
from .paths import PathResolver, check_name
from .types import (
    EntryAlreadyExists,
    EntryNotFound,
    InvalidMove,
    InvalidName,
    Note,
    NotANote,
    HollowConfig,
    HollowError,
)

WELCOME_NAME = "Welcome in Dragon Glass"

WELCOME_CONTENT = """# Welcome in Dragon Glass

This hollow is an ordinary folder of `.md` files, and this note is the only
thing Dragon Glass ever writes into one on its own — so that opening a fresh
hollow is never staring at an empty tree.

A few things worth knowing before you start:

- Type `[[` to link to another note; autocomplete finds it as you type.
- Click a paragraph, heading, list or code block in the preview to edit just
  that block in place.
- Right-click the sidebar — on an entry or on empty space — for what can be
  done to it or made next to it.
- Drop a `.md` note or a `.zip` archive on **Import** in the sidebar: a zip is
  unpacked, and only the notes and images inside it are kept.

Delete this note, or edit it into something else — it will not come back once
the hollow holds another note of its own.
"""


def seed_welcome(resolver: PathResolver, config: HollowConfig) -> None:
    """Write the hollow's first note, when the hollow has nothing in it at all.

    Called once, when the connector opens on an empty directory — a fresh
    hollow, or a fresh volume in a container that has never held one — so that
    a hollow is never blank on the first visit.

    Args:
        resolver: The path resolver opened on the hollow.
        config: The hollow conventions.

    Raises:
        HollowError: The note could not be written.
    """
    filename = config.with_extension(WELCOME_NAME)
    path = resolver.root / filename
    try:
        path.write_text(WELCOME_CONTENT, encoding="utf-8")
    except OSError as error:
        raise HollowError(f"Cannot write '{filename}': {error}") from error


def read(resolver: PathResolver, config: HollowConfig, relative: str) -> Note:
    """Read a note off the disk.

    Args:
        resolver: The path resolver opened on the hollow.
        config: The hollow conventions.
        relative: The hollow-relative path of the note.

    Returns:
        The note, with its Markdown source exactly as stored.

    Raises:
        EntryNotFound: Nothing is at that path.
        NotANote: Something is there, but it is not a note.
        HollowError: The file could not be read.
    """
    path = _require_note(resolver, config, relative)
    try:
        return Note(path=resolver.relative(path), raw=path.read_text(encoding="utf-8"))
    except OSError as error:
        raise HollowError(f"Cannot read '{relative}': {error}") from error
    except UnicodeDecodeError as error:
        raise NotANote(f"'{relative}' is not readable as text") from error


def write(resolver: PathResolver, config: HollowConfig, relative: str, content: str) -> Note:
    """Write a note to the disk, replacing whatever it held.

    Args:
        resolver: The path resolver opened on the hollow.
        config: The hollow conventions.
        relative: The hollow-relative path of the note.
        content: The Markdown to store.

    Returns:
        The note as it now is.

    Raises:
        EntryNotFound: The folder that would hold the note is not there.
        NotANote: The path is not a note path.
        HollowError: The bytes could not be written.
    """
    path = resolver.resolve(relative)
    if not config.is_note(path.name):
        raise NotANote(f"'{relative}' is not a note")
    if not path.parent.is_dir():
        raise EntryNotFound(f"'{resolver.parent_of(relative)}' is not a folder of the hollow")
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        raise HollowError(f"Cannot write '{relative}': {error}") from error
    return Note(path=resolver.relative(path), raw=content)


def create(resolver: PathResolver, config: HollowConfig, parent: str, name: str) -> Note:
    """Create a note, born with its own title as a first-level heading.

    The note extension is appended when the name does not carry it.

    Args:
        resolver: The path resolver opened on the hollow.
        config: The hollow conventions.
        parent: The hollow-relative folder to create it in. Empty is the root.
        name: The name of the note, with or without its extension.

    Returns:
        The note that was created.

    Raises:
        InvalidName: The name cannot be a file name.
        EntryNotFound: The parent folder is not in the hollow.
        EntryAlreadyExists: A file of that name is already there.
        HollowError: The file could not be written.
    """
    filename = config.with_extension(check_name(name))
    check_name(filename)
    folder = resolver.require_directory(parent)
    path = folder / filename
    if path.exists():
        raise EntryAlreadyExists(f"'{filename}' is already in '{parent or 'the root'}'")

    title = config.stem(filename)
    try:
        path.write_text(f"# {title}\n\n", encoding="utf-8")
    except OSError as error:
        raise HollowError(f"Cannot create '{filename}': {error}") from error
    return read(resolver, config, resolver.relative(path))


def create_folder(resolver: PathResolver, parent: str, name: str) -> str:
    """Create a folder inside the hollow.

    Args:
        resolver: The path resolver opened on the hollow.
        parent: The hollow-relative folder to create it in. Empty is the root.
        name: The name of the new folder.

    Returns:
        The hollow-relative path of the folder.

    Raises:
        InvalidName: The name cannot be a folder name.
        EntryNotFound: The parent folder is not in the hollow.
        EntryAlreadyExists: Something of that name is already there.
        HollowError: The folder could not be created.
    """
    folder = resolver.require_directory(parent) / check_name(name)
    if folder.exists():
        raise EntryAlreadyExists(f"'{name}' is already in '{parent or 'the root'}'")
    try:
        folder.mkdir(parents=False)
    except OSError as error:
        raise HollowError(f"Cannot create the folder '{name}': {error}") from error
    return resolver.relative(folder)


def rename(resolver: PathResolver, config: HollowConfig, relative: str, name: str) -> str:
    """Rename a note or a folder in place.

    A note takes its sidecar image folder with it. Renaming a note to the name
    it already has is not an error and changes nothing.

    Args:
        resolver: The path resolver opened on the hollow.
        config: The hollow conventions.
        relative: The hollow-relative path of the entry.
        name: The new name. For a note the extension is appended when missing.

    Returns:
        The hollow-relative path the entry ended up at.

    Raises:
        InvalidName: The new name cannot be used.
        EntryNotFound: The entry is not in the hollow.
        EntryAlreadyExists: The new name is already taken.
        HollowError: The entry could not be renamed.
    """
    source = resolver.require_existing(relative)
    is_note = source.is_file() and config.is_note(source.name)
    wanted = check_name(config.with_extension(name) if is_note else name)
    check_name(wanted)

    destination = source.parent / wanted
    if destination == source:
        return resolver.relative(source)
    if destination.exists():
        raise EntryAlreadyExists(f"'{wanted}' is already in that folder")

    old_path = resolver.relative(source)
    try:
        source.rename(destination)
    except OSError as error:
        raise HollowError(f"Cannot rename '{relative}': {error}") from error

    new_path = resolver.relative(destination)
    if is_note:
        images.follow(resolver, config, old_path, new_path)
    return new_path


def move(resolver: PathResolver, config: HollowConfig, relative: str, parent: str) -> str:
    """Move a note or a folder into another folder.

    Args:
        resolver: The path resolver opened on the hollow.
        config: The hollow conventions.
        relative: The hollow-relative path of the entry.
        parent: The hollow-relative folder to move it into. Empty is the root.

    Returns:
        The hollow-relative path the entry ended up at.

    Raises:
        EntryNotFound: The entry or the destination folder is not in the hollow.
        EntryAlreadyExists: Something of that name is already at the destination.
        InvalidMove: A folder would be moved into itself or into one of its own
            descendants.
        HollowError: The entry could not be moved.
    """
    source = resolver.require_existing(relative)
    destination_folder = resolver.require_directory(parent)
    destination = destination_folder / source.name

    if destination == source:
        return resolver.relative(source)
    if source.is_dir() and destination_folder.is_relative_to(source):
        raise InvalidMove("A folder cannot be moved into itself or into one of its own folders")
    if destination.exists():
        raise EntryAlreadyExists(f"'{source.name}' is already in '{parent or 'the root'}'")

    old_path = resolver.relative(source)
    is_note = source.is_file() and config.is_note(source.name)
    try:
        shutil.move(str(source), str(destination))
    except OSError as error:
        raise HollowError(f"Cannot move '{relative}': {error}") from error

    new_path = resolver.relative(destination)
    if is_note:
        images.follow(resolver, config, old_path, new_path)
    return new_path


def delete(resolver: PathResolver, config: HollowConfig, relative: str) -> None:
    """Delete a note, or a folder and everything under it.

    A note takes its sidecar image folder with it. There is no bin: the files
    leave the disk.

    Args:
        resolver: The path resolver opened on the hollow.
        config: The hollow conventions.
        relative: The hollow-relative path of the entry.

    Raises:
        InvalidPath: The path is the hollow root itself, or leaves the hollow.
        EntryNotFound: The entry is not in the hollow.
        HollowError: The entry could not be removed.
    """
    from .types import InvalidPath

    if not relative.strip().strip("/"):
        raise InvalidPath("The hollow root cannot be deleted")
    target = resolver.require_existing(relative)
    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
            if config.is_note(target.name):
                images.discard(resolver, config, resolver.relative(target))
    except OSError as error:
        raise HollowError(f"Cannot delete '{relative}': {error}") from error


def _require_note(resolver: PathResolver, config: HollowConfig, relative: str) -> Path:
    """Resolve a path that must be an existing note.

    Raises:
        EntryNotFound: Nothing is at that path.
        NotANote: Something is there, but it is not a note file.
    """
    path = resolver.resolve(relative)
    if not path.exists():
        raise EntryNotFound(f"'{relative}' is not in the hollow")
    if not path.is_file() or not config.is_note(path.name):
        raise NotANote(f"'{relative}' is not a note")
    return path
