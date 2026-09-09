"""From a note on disk to what a reader sees.

Rendering is server side on purpose. The client receives finished HTML and does
no Markdown work at all, so the editor and the preview can never disagree about
what a note means.
"""

from __future__ import annotations

import logging
from typing import Final

import markdown

from .blocks import split_blocks
from .extensions import ImagePathExtension, TaskListExtension, WikiLinkExtension
from .types import RenderContext, RenderedBlock, RenderedNote

logger = logging.getLogger(__name__)

DEFAULT_EXTENSIONS: Final = ("fenced_code", "tables", "toc", "sane_lists")
DEFAULT_HOLLOW_ROUTE: Final = "/hollow"


class MarkdownRenderer:
    """Renders notes to HTML, with wiki-links resolved and images pointed home.

    The ``markdown.Markdown`` instance is built once and reused, which is what
    the library is designed for; the per-note information the two Dragon Glass
    extensions need travels in a ``RenderContext`` refreshed before each
    conversion.
    """

    def __init__(
        self,
        extensions: tuple[str, ...] = DEFAULT_EXTENSIONS,
        *,
        wikilinks: bool = True,
        image_paths: bool = True,
        tasklists: bool = True,
        hollow_route: str = DEFAULT_HOLLOW_ROUTE,
    ) -> None:
        """Build the Markdown instance the process will render everything with.

        Args:
            extensions: The names of the Markdown extensions to enable.
            wikilinks: Whether ``[[...]]`` is resolved at all.
            image_paths: Whether relative image paths are rewritten at all.
            tasklists: Whether ``- [x]`` items become checkboxes at all.
            hollow_route: The URL prefix the hollow's files are served under.

        An extension that cannot be loaded is reported and left out rather than
        stopping the process: a mistyped name in the configuration costs that
        one feature, not the server.
        """
        self._context = RenderContext(hollow_route=hollow_route)
        loaded: list[object] = list(self._usable(extensions))
        if wikilinks:
            loaded.append(WikiLinkExtension(self._context))
        if image_paths:
            loaded.append(ImagePathExtension(self._context))
        if tasklists:
            loaded.append(TaskListExtension())
        self._markdown = markdown.Markdown(extensions=loaded, output_format="html")

    @staticmethod
    def _usable(names: tuple[str, ...]) -> list[str]:
        """Keep the named extensions that the Markdown library can actually load."""
        usable: list[str] = []
        for name in names:
            try:
                markdown.Markdown(extensions=[name])
            except Exception as error:  # noqa: BLE001 - any failure means "unusable"
                logger.warning("Markdown extension '%s' could not be loaded: %s", name, error)
                continue
            usable.append(name)
        return usable

    def render(self, path: str, content: str, index=None) -> RenderedNote:
        """Render one note.

        Args:
            path: The hollow-relative path of the note, which is what tells the
                extensions which folder relative links are read from.
            content: The Markdown source.
            index: The note index wiki-links are resolved against. None renders
                every wiki-link as unresolved.

        Returns:
            The note with its HTML beside its source, and the same note cut
            into blocks -- each one rendered on its own, so the preview can
            replace one of them without asking for the page again.
        """
        self._context.folder = path.rsplit("/", 1)[0] if "/" in path else ""
        self._context.index = index
        html = self._convert(content)
        blocks = tuple(
            RenderedBlock(
                start=block.start,
                end=block.end,
                source=block.source,
                html=self._convert(block.source),
            )
            for block in split_blocks(content)
        )
        return RenderedNote(path=path, raw=content, html=html, blocks=blocks)

    def _convert(self, content: str) -> str:
        """Render one piece of Markdown, leaving the instance ready for the next."""
        try:
            return self._markdown.convert(content)
        finally:
            self._markdown.reset()

    def render_note(self, note, index=None) -> RenderedNote:
        """Render a ``Note`` as it came back from the hollow connector."""
        return self.render(note.path, note.raw, index)
