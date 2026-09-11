"""The ``/tutor`` resource: importing a spreadsheet and taking it as a quiz.

Every endpoint is gated behind the ``tutor`` feature toggle -- off, the
resource answers 404 the same as a route that does not exist, so the plugin
stays invisible until it is turned on in the settings panel.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import ValidationError

from connectors.hollow_connector import NoteIndex

from .dependencies import Hollow
from .dependencies_settings import require_feature
from .dependencies_tutor import TutorStore
from .schemas_tutor import (
    TutorAttemptCreate,
    TutorCommit,
    TutorImportOut,
    TutorNoteCreate,
    TutorNoteUpdate,
    TutorQuizOut,
    TutorQuizRename,
    TutorQuizSummaryOut,
    TutorReferenceFolder,
)

router = APIRouter(
    prefix="/tutor",
    tags=["tutor"],
    dependencies=[Depends(require_feature("tutor"))],
)


def _resolve_reference(index: NoteIndex, label: str, folder: str = "") -> str | None:
    """Resolve a reference label to a hollow-relative path.

    Args:
        index: The hollow's note index.
        label: The reference label to resolve -- a note's name or path.
        folder: A hollow-relative folder to restrict the search to, subfolders
            included. Empty searches the whole hollow.

    Returns:
        The path of the first indexed note the label names within scope, or
        None when nothing matches.
    """
    wanted = label.strip().lower()
    if not wanted:
        return None
    stem = wanted[: -len(".md")] if wanted.endswith(".md") else wanted
    matches = [
        note for note in index.notes if note.name.lower() == stem or note.path.lower() == wanted
    ]
    if folder:
        matches = [
            note for note in matches if note.folder == folder or note.folder.startswith(f"{folder}/")
        ]
    return matches[0].path if matches else None


@router.post(
    "/imports",
    response_model=TutorImportOut,
    status_code=status.HTTP_201_CREATED,
    summary="Stage a .csv or .xlsx spreadsheet for column mapping",
)
async def stage_import(
    request: Request,
    tutor: TutorStore,
    file: UploadFile = File(description="A .csv or .xlsx spreadsheet."),
) -> TutorImportOut:
    """Parse an uploaded spreadsheet and hold it in memory for column mapping.

    Args:
        request: The request, read for the configured size limit.
        tutor: The tutor connector.
        file: The uploaded file, sent as ``multipart/form-data``.

    Returns:
        Its header, a short preview of its rows, and the id the mapping step
        commits against.

    Raises:
        HTTPException: The upload is empty, unnamed, or larger than the
            configured limit.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty")

    limit = request.app.state.max_import_bytes
    if len(content) > limit:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"The upload is larger than the {limit} bytes this hollow accepts",
        )

    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file has no name")

    table = tutor.stage_import(file.filename, content)
    return TutorImportOut(
        import_id=table.id,
        filename=table.filename,
        columns=list(table.columns),
        preview_rows=[list(row) for row in table.rows[:5]],
    )


@router.post(
    "/imports/{import_id}/commit",
    response_model=TutorQuizOut,
    status_code=status.HTTP_201_CREATED,
    summary="Map columns and build a quiz set out of a staged import",
)
async def commit_import(
    import_id: str,
    request: Request,
    tutor: TutorStore,
    hollow: Hollow,
    payload: str = Form(description="The column mapping, as JSON -- see TutorCommit."),
    images: list[UploadFile] = File(
        default=[], description="Images to match to questions, when include_images is set."
    ),
) -> TutorQuizOut:
    """Turn a staged import into a persisted quiz set.

    A reference label is resolved against the hollow's note index the same
    way a wiki-link is, so it matches a note by name regardless of which
    folder holds it. An uploaded image is matched to every row whose
    ``image_columns`` cells name it, and stored under the quiz set once it
    is built.

    Args:
        import_id: The staged import to build from.
        request: The request, read for the configured size limit.
        tutor: The tutor connector.
        hollow: The hollow connector, read for its note index.
        payload: The column mapping and the name to give the quiz set, sent
            as a form field carrying JSON since images ride along as files.
        images: The images to match against ``image_columns``, sent as
            ``multipart/form-data``.

    Returns:
        The quiz set that was built and persisted.

    Raises:
        HTTPException: ``payload`` is not valid JSON for a commit, or an
            image is larger than the configured limit.
    """
    try:
        commit = TutorCommit.model_validate_json(payload)
    except ValidationError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    note_index = hollow.index()

    def resolve_reference(label: str) -> str | None:
        return _resolve_reference(note_index, label)

    image_uploads: list[tuple[str, bytes]] = []
    if commit.include_images:
        limit = request.app.state.max_image_bytes
        for image in images:
            content = await image.read()
            if not image.filename or not content:
                continue
            if len(content) > limit:
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    f"'{image.filename}' is larger than the {limit} bytes this hollow accepts",
                )
            image_uploads.append((image.filename, content))

    quiz = tutor.commit_import(
        import_id,
        name=commit.name,
        question_column=commit.question_column,
        answer_columns=tuple(commit.answer_columns),
        correct_column=commit.correct_column,
        reference_column=commit.reference_column,
        reference_separator=commit.reference_separator.strip() if commit.multi_reference else "",
        resolve_reference=resolve_reference,
        image_columns=tuple(commit.image_columns) if commit.include_images else (),
        image_uploads=tuple(image_uploads),
    )
    return TutorQuizOut.model_validate(quiz)


@router.get("/quizzes", response_model=list[TutorQuizSummaryOut], summary="List every quiz set")
def list_quizzes(tutor: TutorStore) -> list[TutorQuizSummaryOut]:
    """Every persisted quiz set, without its questions."""
    return [TutorQuizSummaryOut.model_validate(quiz) for quiz in tutor.list_quizzes()]


@router.get("/quizzes/{quiz_id}", response_model=TutorQuizOut, summary="Read one quiz set")
def get_quiz(quiz_id: str, tutor: TutorStore) -> TutorQuizOut:
    """One persisted quiz set, questions included."""
    return TutorQuizOut.model_validate(tutor.get_quiz(quiz_id))


@router.patch("/quizzes/{quiz_id}", response_model=TutorQuizOut, summary="Rename a quiz set")
def rename_quiz(quiz_id: str, payload: TutorQuizRename, tutor: TutorStore) -> TutorQuizOut:
    """Give a quiz set a new name."""
    return TutorQuizOut.model_validate(tutor.rename_quiz(quiz_id, payload.name))


@router.patch(
    "/quizzes/{quiz_id}/reference-folder",
    response_model=TutorQuizOut,
    summary="Search one folder of the hollow for a quiz's references",
)
def set_reference_folder(
    quiz_id: str,
    payload: TutorReferenceFolder,
    tutor: TutorStore,
    hollow: Hollow,
) -> TutorQuizOut:
    """Re-resolve every question's reference within one folder of the hollow.

    Each question keeps the reference label it was imported with; only the
    path it resolves to is refreshed. Useful when the hollow holds more than
    one note of the same name and the wrong one won on the whole-hollow search.

    Args:
        quiz_id: The quiz set to update.
        payload: The folder to search, subfolders included; empty for the
            whole hollow.
        tutor: The tutor connector.
        hollow: The hollow connector, read for its note index.

    Returns:
        The quiz set, its references refreshed.
    """
    note_index = hollow.index()
    folder = payload.folder.strip().strip("/")

    def resolve_reference(label: str) -> str | None:
        return _resolve_reference(note_index, label, folder)

    quiz = tutor.set_reference_folder(quiz_id, folder, resolve_reference)
    return TutorQuizOut.model_validate(quiz)


@router.post(
    "/quizzes/{quiz_id}/attempts",
    response_model=TutorQuizOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record a completed attempt at a quiz set",
)
def record_attempt(quiz_id: str, payload: TutorAttemptCreate, tutor: TutorStore) -> TutorQuizOut:
    """Record how one run through the quiz went, for its statistics."""
    quiz = tutor.record_attempt(
        quiz_id,
        mode=payload.mode,
        question_count=payload.question_count,
        correct_count=payload.correct_count,
    )
    return TutorQuizOut.model_validate(quiz)


@router.delete(
    "/quizzes/{quiz_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a quiz set",
)
def delete_quiz(quiz_id: str, tutor: TutorStore) -> None:
    """Delete a quiz set."""
    tutor.delete_quiz(quiz_id)


@router.post(
    "/quizzes/{quiz_id}/questions/{question_id}/notes",
    response_model=TutorQuizOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a note to a question, after it has been answered",
)
def add_note(
    quiz_id: str, question_id: str, payload: TutorNoteCreate, tutor: TutorStore
) -> TutorQuizOut:
    """Add a note to a question."""
    return TutorQuizOut.model_validate(tutor.add_note(quiz_id, question_id, payload.text))


@router.patch(
    "/quizzes/{quiz_id}/questions/{question_id}/notes/{note_id}",
    response_model=TutorQuizOut,
    summary="Change one note's text",
)
def update_note(
    quiz_id: str, question_id: str, note_id: str, payload: TutorNoteUpdate, tutor: TutorStore
) -> TutorQuizOut:
    """Change one note's text, independently of the question's other notes."""
    return TutorQuizOut.model_validate(tutor.update_note(quiz_id, question_id, note_id, payload.text))


@router.delete(
    "/quizzes/{quiz_id}/questions/{question_id}/notes/{note_id}",
    response_model=TutorQuizOut,
    summary="Delete one note",
)
def delete_note(quiz_id: str, question_id: str, note_id: str, tutor: TutorStore) -> TutorQuizOut:
    """Delete one note, independently of the question's other notes."""
    return TutorQuizOut.model_validate(tutor.delete_note(quiz_id, question_id, note_id))
