"""The security boundary of the hollow.

Every path arriving from outside the process is resolved and checked against the
hollow root here, before anything is opened. One that would escape raises
``InvalidPath`` and never reaches the disk. This module is the single place that
check is made.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Final

from .types import InvalidName, InvalidPath

RESERVED_NAMES: Final = frozenset({"", ".", ".."})
FORBIDDEN_CHARACTERS: Final = frozenset('/\\:*?"<>|\0')


def check_name(name: str) -> str:
    """Validate a single file or folder name and return it stripped.

    Args:
        name: The proposed name, with no path separator in it.

    Returns:
        The name without its surrounding whitespace.

    Raises:
        InvalidName: The name is empty, is a path component with a meaning of
            its own, holds a character a filesystem will not take, or ends in a
            dot or a space.
    """
    candidate = name.strip()
    if candidate in RESERVED_NAMES:
        raise InvalidName(f"'{name}' is not a usable name")
    if FORBIDDEN_CHARACTERS & set(candidate):
        raise InvalidName(f"'{name}' holds a character a name cannot hold")
    if candidate.endswith((".", " ")):
        raise InvalidName(f"'{name}' cannot end with a dot or a space")
    if len(candidate.encode("utf-8")) > 255:
        raise InvalidName(f"'{name}' is too long for a file name")
    return candidate


def is_valid_name(name: str) -> bool:
    """Whether ``check_name`` would accept the name."""
    try:
        check_name(name)
    except InvalidName:
        return False
    return True


class PathResolver:
    """Turns hollow-relative paths into absolute ones, and refuses the rest.

    The resolver is opened on the hollow root once, and every module of the
    connector goes through it. Nothing else in the project builds a path into
    the hollow by hand.
    """

    def __init__(self, root: Path) -> None:
        """Open the resolver on a hollow root, creating it when it is absent.

        Args:
            root: The directory holding the hollow.

        Raises:
            InvalidPath: The root exists and is not a directory.
        """
        root = root.expanduser()
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise InvalidPath(f"The hollow root {root} is not a directory")
        self._root = root.resolve(strict=True)

    @property
    def root(self) -> Path:
        """The absolute, resolved hollow root."""
        return self._root

    def resolve(self, relative: str) -> Path:
        """Resolve a hollow-relative path into an absolute one inside the hollow.

        Args:
            relative: A POSIX path relative to the hollow root. Empty is the root
                itself; a leading slash is tolerated and means the same thing.

        Returns:
            The absolute path, which may or may not exist.

        Raises:
            InvalidPath: The path is absolute in a way that leaves the hollow,
                walks out of it with ``..``, or lands outside it through a
                symbolic link.
        """
        pure = PurePosixPath(relative.strip().strip("/"))
        if pure.is_absolute():
            raise InvalidPath(f"'{relative}' is not a hollow-relative path")
        parts = [part for part in pure.parts if part not in {"", "."}]
        if any(part == ".." for part in parts):
            raise InvalidPath(f"'{relative}' walks out of the hollow")
        if any("\0" in part for part in parts):
            raise InvalidPath("A path cannot hold a null byte")

        candidate = self._root.joinpath(*parts)
        try:
            resolved = candidate.resolve()
        except OSError as error:
            raise InvalidPath(f"'{relative}' cannot be resolved: {error}") from error
        if resolved != self._root and not resolved.is_relative_to(self._root):
            raise InvalidPath(f"'{relative}' leaves the hollow")
        return resolved

    def relative(self, absolute: Path) -> str:
        """Return the hollow-relative POSIX path of an absolute one.

        Args:
            absolute: A path inside the hollow.

        Returns:
            The path relative to the root, empty for the root itself.

        Raises:
            InvalidPath: The path is not inside the hollow.
        """
        try:
            return absolute.relative_to(self._root).as_posix().removeprefix(".")
        except ValueError as error:
            raise InvalidPath(f"{absolute} is not inside the hollow") from error

    def join(self, parent: str, name: str) -> str:
        """Join a hollow-relative parent and a name into a hollow-relative path."""
        parent = parent.strip().strip("/")
        return f"{parent}/{name}" if parent else name

    @staticmethod
    def parent_of(path: str) -> str:
        """The hollow-relative folder holding a path, empty at the root."""
        path = path.strip().strip("/")
        return path.rsplit("/", 1)[0] if "/" in path else ""

    @staticmethod
    def name_of(path: str) -> str:
        """The last component of a hollow-relative path."""
        return path.strip().strip("/").rsplit("/", 1)[-1]

    def require_directory(self, relative: str) -> Path:
        """Resolve a path that must be an existing directory.

        Raises:
            EntryNotFound: Nothing is there, or what is there is not a folder.
        """
        from .types import EntryNotFound

        resolved = self.resolve(relative)
        if not resolved.is_dir():
            raise EntryNotFound(f"'{relative}' is not a folder of the hollow")
        return resolved

    def require_existing(self, relative: str) -> Path:
        """Resolve a path that must exist.

        Raises:
            EntryNotFound: Nothing is there.
        """
        from .types import EntryNotFound

        resolved = self.resolve(relative)
        if not resolved.exists():
            raise EntryNotFound(f"'{relative}' is not in the hollow")
        return resolved
