"""The ``[[...]]`` inline pattern.

A wiki-link is written ``[[Note name]]``, or ``[[Note name|the text to show]]``.
The name is resolved against the index of every note in the hollow, and a note of
the same name in the same folder as the one being read wins. A link that
resolves to nothing is rendered as unresolved rather than dropped, with a class
the frontend styles differently and turns into an offer to create the note.
"""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from typing import Final

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor

from ..types import LinkTarget, RenderContext

WIKILINK_PATTERN: Final = r"\[\[([^\[\]|\n]+?)(?:\|([^\[\]\n]*?))?\]\]"
RESOLVED_CLASS: Final = "wikilink"
UNRESOLVED_CLASS: Final = "wikilink wikilink-unresolved"


def resolve(context: RenderContext, name: str, label: str | None) -> LinkTarget:
    """Resolve one wiki-link against the context's index.

    Args:
        context: The note currently being rendered.
        name: The name written between the brackets.
        label: The text after the pipe, if the link carried one.

    Returns:
        The link target, unresolved when the index holds nothing of that name.
    """
    name = name.strip()
    shown = (label or "").strip() or name
    index = context.index
    found = index.resolve(name, context.folder) if index is not None else None
    return LinkTarget(name=name, label=shown, path=found.path if found else None)


class WikiLinkProcessor(InlineProcessor):
    """Turns one ``[[...]]`` occurrence into an anchor element."""

    def __init__(self, pattern: str, md, context: RenderContext) -> None:
        """Bind the processor to the context the renderer refreshes per note."""
        super().__init__(pattern, md)
        self._context = context

    def handleMatch(self, m, data):  # noqa: N802 - the Markdown API names it
        """Build the anchor for a matched wiki-link.

        Returns:
            The element and the span it consumed, as the Markdown API expects.
        """
        target = resolve(self._context, m.group(1), m.group(2))
        element = ElementTree.Element("a")
        element.text = target.label
        element.set("data-wikilink", target.name)
        if target.resolved:
            element.set("href", f"#{target.path}")
            element.set("data-path", target.path or "")
            element.set("class", RESOLVED_CLASS)
            element.set("title", target.path or "")
        else:
            element.set("href", "#")
            element.set("class", UNRESOLVED_CLASS)
            element.set("title", f"{target.name} — note not found")
        return element, m.start(0), m.end(0)


class WikiLinkExtension(Extension):
    """Installs the wiki-link inline pattern into a Markdown instance."""

    def __init__(self, context: RenderContext) -> None:
        """Bind the extension to the render context it reads the index from."""
        super().__init__()
        self._context = context

    def extendMarkdown(self, md) -> None:  # noqa: N802 - the Markdown API names it
        """Register the pattern ahead of the built-in link syntax."""
        md.inlinePatterns.register(
            WikiLinkProcessor(WIKILINK_PATTERN, md, self._context),
            "dragonglass_wikilink",
            175,
        )
