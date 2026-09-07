"""Turning ``- [x]`` and ``- [ ]`` list items into real checkboxes.

Markdown has no task lists of its own: a list item written ``- [x] done`` comes
out of the parser with the brackets still in it, as text. This walks the
rendered tree afterwards and swaps that opening ``[x]`` for a checkbox, leaving
the rest of the line exactly as the parser built it.

The boxes are rendered disabled. A note is edited as Markdown, so ticking one in
the preview would be a change the file never heard about.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree
from typing import Final

from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

TASK_PATTERN: Final = re.compile(r"^\s*\[(?P<state>[ xX])\](?=\s|$)\s*")

LIST_CLASS: Final = "task-list"
ITEM_CLASS: Final = "task-list-item"


def _holder(item: ElementTree.Element) -> ElementTree.Element | None:
    """The element whose text begins a list item, or None when it has no text.

    A tight list puts the text on the ``<li>`` itself; a loose one wraps it in a
    ``<p>`` first, and the brackets are then at the start of that paragraph.
    """
    if item.text and item.text.strip():
        return item
    if len(item) and item[0].tag == "p":
        return item[0]
    return None


def _with_class(element: ElementTree.Element, name: str) -> None:
    """Add a class to an element, keeping whatever classes it already carries."""
    existing = element.get("class", "").split()
    if name not in existing:
        existing.append(name)
    element.set("class", " ".join(existing))


class TaskListProcessor(Treeprocessor):
    """Replaces the leading ``[x]`` of every list item that has one."""

    def run(self, root):
        """Walk every list of the note and turn its task items into checkboxes."""
        for parent in root.iter():
            if parent.tag not in {"ul", "ol"}:
                continue
            for item in parent:
                if item.tag == "li" and self._convert(item):
                    _with_class(parent, LIST_CLASS)
        return root

    @staticmethod
    def _convert(item: ElementTree.Element) -> bool:
        """Turn one list item into a task item, if it is written as one.

        Returns:
            Whether the item carried a task marker and was converted.
        """
        holder = _holder(item)
        if holder is None:
            return False

        match = TASK_PATTERN.match(holder.text or "")
        if match is None:
            return False

        checkbox = ElementTree.Element("input", {"type": "checkbox", "disabled": "disabled"})
        if match.group("state").lower() == "x":
            checkbox.set("checked", "checked")

        # An element's text comes before its children, so what is left of the
        # line has to travel on the checkbox's tail to stay after it.
        checkbox.tail = (holder.text or "")[match.end() :]
        holder.text = ""
        holder.insert(0, checkbox)
        _with_class(item, ITEM_CLASS)
        return True


class TaskListExtension(Extension):
    """Installs the task-list rewriting into a Markdown instance."""

    def extendMarkdown(self, md) -> None:  # noqa: N802 - the Markdown API names it
        """Register the tree processor after the lists have been built."""
        md.treeprocessors.register(TaskListProcessor(md), "dragonglass_tasklists", 4)
