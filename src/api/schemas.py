"""The payloads the hollow's own API takes and gives back, and nothing else.

The settings and tutor plugins keep their own payloads in
``schemas_settings.py`` and ``schemas_tutor.py``, so this module never grows
to know about a plugin that gets added or removed.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TreeNode(BaseModel):
    """One node of the hollow tree."""

    model_config = ConfigDict(from_attributes=True)

    kind: Literal["folder", "note", "image"] = Field(description="What the node is.")
    name: str = Field(description="The name on disk, extension included.")
    path: str = Field(description="The hollow-relative path of the node.")
    children: list[TreeNode] | None = Field(
        default=None,
        description="The nodes below a folder; absent for notes and images.",
    )


class NoteBlock(BaseModel):
    """One block of a note: its Markdown, where it sits, and its HTML."""

    model_config = ConfigDict(from_attributes=True)

    start: int = Field(description="The offset the block starts at in the Markdown source.")
    end: int = Field(
        description="The offset just past its last character, so an edited block can be "
        "written back into the source without disturbing what surrounds it.",
    )
    source: str = Field(description="The Markdown the block is written in.")
    html: str = Field(description="That block rendered on its own.")


class NoteOut(BaseModel):
    """A note, with the HTML already rendered."""

    path: str = Field(description="The hollow-relative path the note lives at.")
    raw: str = Field(description="The Markdown source, exactly as stored.")
    html: str = Field(description="The rendered HTML, links resolved and images pointed home.")
    blocks: list[NoteBlock] = Field(
        default_factory=list,
        description="The same note cut into the blocks the preview edits one at a time.",
    )


class NoteUpdate(BaseModel):
    """The body of a save."""

    content: str = Field(description="The Markdown to store.")


class NoteRender(BaseModel):
    """The body of a render: Markdown that has not been saved anywhere."""

    content: str = Field(description="The Markdown to render.")


class NoteCreate(BaseModel):
    """The body of a note creation."""

    parent: str = Field(default="", description="The folder to create it in. Empty is the root.")
    name: str = Field(min_length=1, description="The note name, with or without its extension.")


class FolderCreate(BaseModel):
    """The body of a folder creation."""

    parent: str = Field(default="", description="The folder to create it in. Empty is the root.")
    name: str = Field(min_length=1, description="The name of the new folder.")


class EntryOut(BaseModel):
    """Where an entry ended up after a rename or a move."""

    path: str = Field(description="The hollow-relative path of the entry.")
    name: str = Field(description="Its name, extension included.")


class EntryRename(BaseModel):
    """The body of a rename."""

    name: str = Field(min_length=1, description="The new name of the entry.")


class EntryMove(BaseModel):
    """The body of a move."""

    parent: str = Field(default="", description="The folder to move it into. Empty is the root.")


class ImageOut(BaseModel):
    """An uploaded image, ready to be written into the Markdown."""

    name: str = Field(description="The name the file was given, sanitised and de-duplicated.")
    path: str = Field(description="The hollow-relative path of the file.")


class ImportOut(BaseModel):
    """What an upload produced."""

    created: list[str] = Field(
        description="The hollow-relative paths that were written -- a single note, or every "
        "note and image a .zip unpacked into.",
    )
    skipped: int = Field(
        default=0,
        description="Entries of an archive that were neither a note nor an image, and so were "
        "left out.",
    )
