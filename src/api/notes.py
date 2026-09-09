"""The ``/notes`` resource: reading a note, saving one, creating one, rendering one.

A save is not a write. ``PUT /notes/{path}`` does four things, in this order
because each one needs the last: the title claims the filename, the bytes land,
the index is refreshed, and the Markdown is rendered. The response carries the
note back whole, with the **new** path when the first step moved it -- so the
client replaces what it holds with what came back rather than guessing what the
server did.

Every answer carries the note cut into blocks as well as rendered whole, and
``POST /notes/{path}/render`` gives back the same thing for Markdown that was
never saved -- which is how the preview shows an edited block again the moment
it stops being edited, without the file having heard about it yet.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from core.types import RenderedNote

from .dependencies import Renderer, Titles, Hollow
from .schemas import NoteBlock, NoteCreate, NoteOut, NoteRender, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


def _answer(rendered: RenderedNote) -> NoteOut:
    """The one shape every note answer has: the source, the page, and the blocks."""
    return NoteOut(
        path=rendered.path,
        raw=rendered.raw,
        html=rendered.html,
        blocks=[NoteBlock.model_validate(block) for block in rendered.blocks],
    )


@router.get("/{path:path}", response_model=NoteOut, summary="Read a note")
def read_note(path: str, hollow: Hollow, renderer: Renderer) -> NoteOut:
    """Return one note with its HTML already rendered.

    Args:
        path: The hollow-relative path of the note.
        hollow: The hollow connector.
        renderer: The Markdown renderer.

    Returns:
        The note's path, its Markdown source and the rendered HTML.
    """
    note = hollow.read_note(path)
    return _answer(renderer.render_note(note, hollow.index()))


@router.put("/{path:path}", response_model=NoteOut, summary="Save a note")
def save_note(
    path: str,
    payload: NoteUpdate,
    hollow: Hollow,
    renderer: Renderer,
    titles: Titles,
) -> NoteOut:
    """Save a note, letting its title claim the filename first.

    Args:
        path: The hollow-relative path the note is at now.
        payload: The Markdown to store.
        hollow: The hollow connector.
        renderer: The Markdown renderer.
        titles: The title-to-filename sync.

    Returns:
        The note as it now is, at the path it ended up at -- which is a new one
        when the title renamed the file.
    """
    synced = titles.sync(hollow, path, payload.content)
    note = hollow.write_note(synced.path, synced.content)
    return _answer(renderer.render_note(note, hollow.index()))


@router.post("/{path:path}/render", response_model=NoteOut, summary="Render a note unsaved")
def render_note(path: str, payload: NoteRender, hollow: Hollow, renderer: Renderer) -> NoteOut:
    """Render Markdown as the note at ``path`` without writing anything.

    Args:
        path: The hollow-relative path the Markdown belongs to, which is what
            tells wiki-links and image paths where they are read from.
        payload: The Markdown to render.
        hollow: The hollow connector.
        renderer: The Markdown renderer.

    Returns:
        The same answer a read gives, blocks included -- what the preview asks
        for after a block was edited in place, while the note on disk is still
        the one it was.
    """
    return _answer(renderer.render(path, payload.content, hollow.index()))


@router.post(
    "",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a note",
)
def create_note(payload: NoteCreate, hollow: Hollow, renderer: Renderer) -> NoteOut:
    """Create a note, born with its own title as a first-level heading.

    Args:
        payload: The parent folder and the name of the note.
        hollow: The hollow connector.
        renderer: The Markdown renderer.

    Returns:
        The note that was created, rendered.
    """
    note = hollow.create_note(payload.parent, payload.name)
    return _answer(renderer.render_note(note, hollow.index()))
