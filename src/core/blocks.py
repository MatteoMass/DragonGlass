"""Where one block of a note ends and the next begins.

A note is read as one page but written a paragraph at a time, so the preview
needs to know which piece of Markdown produced which piece of the page. This
cuts the source into the top-level blocks it is written in and remembers where
each one sits, which is what lets an edited block be written back into the file
by its offsets -- everything around it, blank lines included, stays exactly as
it was.
"""

from __future__ import annotations

import re
from typing import Final

from .types import SourceBlock

FENCE: Final = re.compile(r"^ {0,3}(?P<marker>`{3,}|~{3,})")


def _closes(line: str, fence: str) -> bool:
    """Whether a line is the closing marker of the fenced block ``fence`` opened."""
    stripped = line.strip()
    return len(stripped) >= len(fence) and set(stripped) == {fence[0]}


def split_blocks(source: str) -> list[SourceBlock]:
    """Cut a note into the blocks it is written in.

    Args:
        source: The Markdown source of the whole note.

    Returns:
        The blocks in the order they appear, each with the offsets it occupies
        in ``source``.

    A blank line ends a block, except inside a fenced code block where blank
    lines are part of the code. The blank lines between blocks belong to no
    block: they are what is left alone when one block is replaced.
    """
    blocks: list[SourceBlock] = []
    offset = 0
    start: int | None = None
    end = 0
    fence: str | None = None

    for line in source.splitlines(keepends=True):
        blank = not line.strip()
        if fence is None and blank:
            if start is not None:
                blocks.append(SourceBlock(start=start, end=end, source=source[start:end]))
                start = None
        else:
            if start is None:
                start = offset
            end = offset + len(line.rstrip("\r\n"))
            if fence is None:
                opening = FENCE.match(line)
                if opening:
                    fence = opening.group("marker")
            elif _closes(line, fence):
                fence = None
        offset += len(line)

    if start is not None:
        blocks.append(SourceBlock(start=start, end=end, source=source[start:end]))
    return blocks
