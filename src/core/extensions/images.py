"""Rewriting relative image paths towards the ``/hollow/...`` route.

A note refers to its pictures the way a file on disk does -- ``![x](X_images/x.png)``
-- and the browser needs a URL. Absolute URLs, explicit protocols and ``data:``
URIs are left exactly as they were written.
"""

from __future__ import annotations

from posixpath import normpath
from typing import Final
from urllib.parse import quote

from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

from ..types import RenderContext

UNTOUCHED_PREFIXES: Final = ("http://", "https://", "data:", "//", "/")


def is_external(source: str) -> bool:
    """Whether an image source is one the rewriting must leave alone."""
    lowered = source.strip().lower()
    if lowered.startswith(UNTOUCHED_PREFIXES):
        return True
    scheme, separator, _ = lowered.partition(":")
    return bool(separator) and scheme.isalpha()


def to_hollow_url(context: RenderContext, source: str) -> str:
    """Turn one relative image path into a URL under the hollow route.

    The path is taken relative to the folder of the note being rendered, then
    normalised and percent-encoded per segment.

    Args:
        context: The note currently being rendered.
        source: The path as it is written in the Markdown.

    Returns:
        The URL to put in the ``src`` attribute. A path that would climb out of
        the hollow is returned untouched, because there is no correct URL for it
        and silently pointing elsewhere would be worse.
    """
    candidate = source.strip()
    if not candidate or is_external(candidate):
        return source

    joined = f"{context.folder}/{candidate}" if context.folder else candidate
    normalised = normpath(joined)
    if normalised.startswith("..") or normalised == ".":
        return source

    encoded = "/".join(quote(part) for part in normalised.split("/"))
    return f"{context.hollow_route.rstrip('/')}/{encoded}"


class ImagePathProcessor(Treeprocessor):
    """Rewrites the ``src`` of every image of one rendered note."""

    def __init__(self, md, context: RenderContext) -> None:
        """Bind the processor to the context the renderer refreshes per note."""
        super().__init__(md)
        self._context = context

    def run(self, root):
        """Walk the rendered tree and point every relative image at the hollow."""
        for element in root.iter("img"):
            source = element.get("src")
            if source:
                element.set("src", to_hollow_url(self._context, source))
        return root


class ImagePathExtension(Extension):
    """Installs the image-path rewriting into a Markdown instance."""

    def __init__(self, context: RenderContext) -> None:
        """Bind the extension to the render context it reads the folder from."""
        super().__init__()
        self._context = context

    def extendMarkdown(self, md) -> None:  # noqa: N802 - the Markdown API names it
        """Register the tree processor after the inline pass has built the images."""
        md.treeprocessors.register(
            ImagePathProcessor(md, self._context),
            "dragonglass_image_paths",
            5,
        )
