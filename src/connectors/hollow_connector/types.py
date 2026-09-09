"""What the hollow connector hands out, and what it raises.

The errors are named for what is missing rather than suffixed ``...Error``, and
they are the vocabulary the API translates into status codes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HollowError(Exception):
    """Base of everything the hollow connector raises."""


class EntryNotFound(HollowError):
    """Nothing exists at the requested path."""


class EntryAlreadyExists(HollowError):
    """Something already occupies the requested path."""


class InvalidName(HollowError):
    """The proposed name cannot be a file or a folder name."""


class InvalidPath(HollowError):
    """The path is malformed, or would leave the hollow root."""


class InvalidMove(HollowError):
    """The move cannot be made -- a folder into itself or into a descendant."""


class NotANote(HollowError):
    """The entry exists but is not a note."""


class EntryKind(StrEnum):
    """What a node of the tree is."""

    FOLDER = "folder"
    NOTE = "note"
    IMAGE = "image"


@dataclass(frozen=True, slots=True)
class Entry:
    """One node of the hollow tree.

    Attributes:
        kind: Whether the node is a folder, a note or an image.
        name: The name on disk, extension included.
        path: The hollow-relative POSIX path of the node.
        children: The nodes below a folder; None for notes and images.
    """

    kind: EntryKind
    name: str
    path: str
    children: tuple[Entry, ...] | None = None


@dataclass(frozen=True, slots=True)
class Note:
    """A note as it is on disk.

    Attributes:
        path: The hollow-relative POSIX path of the note.
        raw: The Markdown source, exactly as stored.
    """

    path: str
    raw: str

    @property
    def name(self) -> str:
        """The note's name, without its extension."""
        return self.path.rsplit("/", 1)[-1].rsplit(".", 1)[0]

    @property
    def folder(self) -> str:
        """The hollow-relative folder holding the note, empty at the root."""
        return self.path.rsplit("/", 1)[0] if "/" in self.path else ""


@dataclass(frozen=True, slots=True)
class IndexedNote:
    """One entry of the note index.

    Attributes:
        name: The note's name without its extension, which is what a wiki-link
            is written with.
        folder: The hollow-relative folder holding it, empty at the root.
        path: The hollow-relative POSIX path of the note.
    """

    name: str
    folder: str
    path: str


@dataclass(frozen=True, slots=True)
class NoteIndex:
    """The flat list of every note in the hollow, and how a name is resolved.

    Attributes:
        notes: Every note in the hollow, sorted by path.
    """

    notes: tuple[IndexedNote, ...] = ()

    def resolve(self, name: str, folder: str = "") -> IndexedNote | None:
        """Resolve a wiki-link name against the index.

        A note of the same name in ``folder`` wins over one anywhere else, so a
        ``Roadmap`` linked from inside ``Projects/`` is that project's roadmap
        and not the one three folders away. Matching ignores case, and a name
        written with its extension resolves the same as one without.

        Args:
            name: The name as written between the brackets.
            folder: The hollow-relative folder of the note being read.

        Returns:
            The note the name points at, or None when nothing carries it.
        """
        wanted = name.strip().lower()
        if not wanted:
            return None
        stem = wanted[: -len(".md")] if wanted.endswith(".md") else wanted
        matches = [
            note
            for note in self.notes
            if note.name.lower() == stem or note.path.lower() == wanted
        ]
        if not matches:
            return None
        for note in matches:
            if note.folder == folder:
                return note
        return matches[0]

    def names(self) -> tuple[str, ...]:
        """Every note name in the index, in index order."""
        return tuple(note.name for note in self.notes)


@dataclass(frozen=True, slots=True)
class UploadedImage:
    """An image that has just landed in a note's sidecar folder.

    Attributes:
        name: The name the file was given, sanitised and de-duplicated.
        path: The hollow-relative POSIX path of the file.
    """

    name: str
    path: str


@dataclass(frozen=True, slots=True)
class ImportResult:
    """What an upload produced.

    Attributes:
        created: The hollow-relative paths that were written -- a single note,
            or every note and image a ``.zip`` unpacked into.
        skipped: How many entries of an archive were neither a note nor an
            image, by the hollow's own conventions, and so were left out.
    """

    created: tuple[str, ...]
    skipped: int = 0


@dataclass(frozen=True, slots=True)
class HollowConfig:
    """The conventions the connector applies to the directory it serves.

    Attributes:
        note_extension: The extension that makes a file a note.
        images_suffix: The suffix of a note's sidecar image folder.
        image_extensions: The extensions that appear in the tree as images.
    """

    note_extension: str = ".md"
    images_suffix: str = "_images"
    image_extensions: tuple[str, ...] = (
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".bmp",
    )

    def is_note(self, name: str) -> bool:
        """Whether a file name is a note."""
        return name.lower().endswith(self.note_extension.lower())

    def is_image(self, name: str) -> bool:
        """Whether a file name is an image the tree shows."""
        lowered = name.lower()
        return any(lowered.endswith(extension) for extension in self.image_extensions)

    def images_folder_name(self, note_name: str) -> str:
        """The name of the sidecar folder belonging to a note file name."""
        return f"{self.stem(note_name)}{self.images_suffix}"

    def stem(self, note_name: str) -> str:
        """A note file name without its extension."""
        if self.is_note(note_name):
            return note_name[: -len(self.note_extension)]
        return note_name

    def with_extension(self, name: str) -> str:
        """A note name with its extension, appended when it is missing."""
        return name if self.is_note(name) else f"{name}{self.note_extension}"
