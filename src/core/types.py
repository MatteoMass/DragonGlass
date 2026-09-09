"""What crosses the boundary of the core layer.

Nothing here knows about HTTP, and nothing here knows where the bytes came from.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LinkTarget:
    """What a ``[[wiki-link]]`` was found to point at.

    Attributes:
        name: The note name as it was written between the brackets.
        label: The text to show, which is the name unless the link gave one.
        path: The hollow-relative path of the note, or None when the name
            resolves to nothing and the link is rendered as unresolved.
    """

    name: str
    label: str
    path: str | None = None

    @property
    def resolved(self) -> bool:
        """Whether the link points at a note that exists."""
        return self.path is not None


@dataclass(frozen=True, slots=True)
class SourceBlock:
    """One block of a note's Markdown, and where it sits in the source.

    Attributes:
        start: The offset the block starts at, in characters.
        end: The offset just past its last character, the line break that
            follows excluded -- so replacing ``source[start:end]`` leaves the
            blank lines around the block where they are.
        source: The Markdown the block is written in.
    """

    start: int
    end: int
    source: str


@dataclass(frozen=True, slots=True)
class RenderedBlock:
    """One block of a note, with the HTML it renders to on its own.

    Attributes:
        start: The offset the block starts at, in characters.
        end: The offset just past its last character.
        source: The Markdown the block is written in.
        html: That block rendered by itself, which is what the preview shows
            in its place and replaces when the block is edited.
    """

    start: int
    end: int
    source: str
    html: str


@dataclass(frozen=True, slots=True)
class RenderedNote:
    """A note and the HTML it renders to.

    Attributes:
        path: The hollow-relative path the note lives at.
        raw: The Markdown source, exactly as stored.
        html: The rendered HTML, with wiki-links resolved and image paths
            rewritten towards the ``/hollow/...`` route.
        blocks: The same note cut into the blocks it is written in, each one
            rendered on its own, which is what the preview edits in place.
    """

    path: str
    raw: str
    html: str
    blocks: tuple[RenderedBlock, ...] = ()


@dataclass(slots=True)
class RenderContext:
    """What the extensions need to know about the note being rendered.

    One instance is held by the renderer and refreshed before each conversion,
    because the ``markdown.Markdown`` instance is built once and reused.

    Attributes:
        folder: The hollow-relative folder holding the note, empty at the root.
        index: The note index wiki-links are resolved against.
        hollow_route: The URL prefix the hollow's files are served under.
    """

    folder: str = ""
    index: object | None = None
    hollow_route: str = "/hollow"
