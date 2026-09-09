"""The title-to-filename sync, and the image references a rename implies.

A note is named by editing it, not by a dialog: the first-level ``# Heading`` is
compared with the name of the file, and when they disagree the file is renamed
to match the title. The sidecar image folder is renamed with it, and the image
references in the body are rewritten to point at the new folder.

If the target name is taken or is not a usable filename the rename is skipped
and the content is saved as it stands -- saving never fails because of a title.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Final, Protocol
from urllib.parse import quote, unquote

logger = logging.getLogger(__name__)

TITLE_PATTERN: Final = re.compile(r"^[ \t]{0,3}#[ \t]+(?P<title>.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
FENCE_PATTERN: Final = re.compile(r"^[ \t]{0,3}(?P<fence>```+|~~~+)", re.MULTILINE)


class NoteRenamer(Protocol):
    """The only thing the title sync needs from whatever holds the notes.

    The core layer does not know that a note is a file; it knows that something
    can rename one and say where it ended up.
    """

    def rename_entry(self, path: str, name: str) -> str:
        """Rename the entry at ``path`` to ``name`` and return its new path."""
        ...


@dataclass(frozen=True, slots=True)
class TitleSync:
    """What the sync decided.

    Attributes:
        path: The path the note ended up at -- the new one when it moved, the
            old one when nothing happened.
        content: The Markdown to store, with its image references rewritten when
            the sidecar folder moved with the note.
        renamed: Whether the file was actually renamed.
    """

    path: str
    content: str
    renamed: bool = False


def extract_title(content: str) -> str | None:
    """Return the first-level heading of a note, if it has one.

    Headings inside fenced code blocks are not titles, so the search stops at
    the first fence.

    Args:
        content: The Markdown source.

    Returns:
        The text of the first ``# Heading``, or None when there is none.
    """
    fence = FENCE_PATTERN.search(content)
    searchable = content[: fence.start()] if fence else content
    match = TITLE_PATTERN.search(searchable)
    if match is None:
        return None
    title = match.group("title").strip()
    return title or None


def rewrite_image_references(content: str, old_folder: str, new_folder: str) -> str:
    """Point the image references of a note at its renamed sidecar folder.

    Both the raw and the percent-encoded spelling of the old folder name are
    replaced, because a path written by hand and one written by the upload
    button do not look the same.

    Args:
        content: The Markdown source.
        old_folder: The sidecar folder name the note used to have.
        new_folder: The one it has now.

    Returns:
        The source with every reference to the old folder pointing at the new one.
    """
    if old_folder == new_folder:
        return content
    spellings = {old_folder, quote(old_folder), unquote(old_folder)}
    for spelling in spellings:
        if not spelling:
            continue
        replacement = quote(new_folder) if spelling != old_folder else new_folder
        content = content.replace(f"{spelling}/", f"{replacement}/")
    return content


class TitleSynchroniser:
    """Keeps a note's filename equal to its own first-level heading."""

    def __init__(
        self,
        *,
        note_extension: str = ".md",
        images_suffix: str = "_images",
        enabled: bool = True,
    ) -> None:
        """Configure the sync with the hollow's naming conventions.

        Args:
            note_extension: The extension a note file carries.
            images_suffix: The suffix of a note's sidecar image folder.
            enabled: Whether a save is allowed to rename the file at all. When
                this is off, ``sync`` returns the note unchanged.
        """
        self._note_extension = note_extension
        self._images_suffix = images_suffix
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        """Whether a save is allowed to rename the file after its title."""
        return self._enabled

    def sync(self, renamer: NoteRenamer, path: str, content: str) -> TitleSync:
        """Let the title of a note claim the name of its file.

        This runs before the bytes land, so the rename acts on the file as it
        already is and the content is then written at the path this returns.

        Args:
            renamer: Whatever can rename a note and say where it went.
            path: The hollow-relative path the note is at now.
            content: The Markdown about to be saved.

        Returns:
            The path to write at and the content to write, with ``renamed``
            saying whether the file moved. Any refusal from the renamer -- a
            taken name, an unusable one -- is logged and answered with the note
            exactly as it came in.
        """
        unchanged = TitleSync(path=path, content=content)
        if not self._enabled:
            return unchanged

        title = extract_title(content)
        if title is None:
            return unchanged

        current_name = path.rsplit("/", 1)[-1]
        current_stem = self._stem(current_name)
        if title == current_stem:
            return unchanged

        try:
            new_path = renamer.rename_entry(path, title)
        except Exception as error:  # noqa: BLE001 - a rename never fails a save
            logger.info("The title of '%s' could not claim the filename: %s", path, error)
            return unchanged

        if new_path == path:
            return unchanged

        new_stem = self._stem(new_path.rsplit("/", 1)[-1])
        rewritten = rewrite_image_references(
            content,
            f"{current_stem}{self._images_suffix}",
            f"{new_stem}{self._images_suffix}",
        )
        logger.info("'%s' renamed itself to '%s'", path, new_path)
        return TitleSync(path=new_path, content=rewritten, renamed=True)

    def _stem(self, name: str) -> str:
        """A note file name without its extension."""
        if name.lower().endswith(self._note_extension.lower()):
            return name[: -len(self._note_extension)]
        return name
