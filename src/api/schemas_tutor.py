"""The payloads the ``/tutor`` resource takes and gives back, and nothing else."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class TutorImportOut(BaseModel):
    """A spreadsheet staged for column mapping, before it becomes a quiz."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    import_id: str = Field(description="The id this staged import is held under.")
    filename: str = Field(description="The name the upload arrived with.")
    columns: list[str] = Field(description="The header row.")
    preview_rows: list[list[str]] = Field(
        description="The first few data rows, shown while columns are picked.",
    )


class TutorCommit(BaseModel):
    """The body that turns a staged import into a quiz set."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str = Field(default="", description="The name to give the quiz set.")
    question_column: str = Field(description="The column holding each question's text.")
    answer_columns: list[str] = Field(
        min_length=2,
        description="The columns holding each answer, in display order.",
    )
    correct_column: str = Field(description="The column naming the correct answer of each row.")
    reference_column: str | None = Field(
        default=None,
        description="The column holding a reference note's name, if any.",
    )
    multi_reference: bool = Field(
        default=False,
        description="Whether the reference column may name more than one source, "
        "joined by reference_separator.",
    )
    reference_separator: str = Field(
        default=";",
        description="The literal that splits a reference label into several source "
        "names, used only when multi_reference is set.",
    )
    include_images: bool = Field(
        default=False,
        description="Whether images uploaded alongside this mapping should be matched "
        "to the rows that name them.",
    )
    image_columns: list[str] = Field(
        default_factory=list,
        description="The columns to search for an uploaded image's name, used only when "
        "include_images is set. Usually the question column, but answer columns may be "
        "included too.",
    )


class TutorNoteOut(BaseModel):
    """One note left on a question, after it was answered."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: str = Field(description="The note's id, stable within its question.")
    text: str = Field(description="The note's text.")
    created_at: str = Field(description="When it was written, ISO 8601.")


class TutorNoteCreate(BaseModel):
    """The body that adds a note to a question."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    text: str = Field(min_length=1, description="The note's text.")


class TutorNoteUpdate(BaseModel):
    """The body that changes a note's text."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    text: str = Field(min_length=1, description="The note's new text.")


class TutorQuestionOut(BaseModel):
    """One question of a quiz set."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: str = Field(description="The question's id, stable within its quiz set.")
    question: str = Field(description="The question text.")
    answers: list[str] = Field(description="The possible answers, in the order they show.")
    correct_indices: list[int] = Field(
        description="The indices into answers that are correct -- more than one for a "
        "question the correct-answer column named several answers for.",
    )
    reference: str = Field(default="", description="The reference label, empty when there was none.")
    reference_paths: list[str] = Field(
        default_factory=list,
        description="The hollow-relative paths each source in reference resolved to; a "
        "source that matched nothing is left out.",
    )
    notes: list[TutorNoteOut] = Field(
        default_factory=list,
        description="The notes left on this question, oldest first.",
    )
    image_paths: list[str] = Field(
        default_factory=list,
        description="The tutor-relative paths of the images matched to this question "
        "at import time, in upload order.",
    )


class TutorQuizRename(BaseModel):
    """The body of a rename."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str = Field(min_length=1, description="The new name of the quiz set.")


class TutorReferenceFolder(BaseModel):
    """The body that re-scopes a quiz set's references to one folder."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    folder: str = Field(
        default="",
        description="The hollow-relative folder to search, subfolders included. Empty "
        "searches the whole hollow.",
    )


class TutorAttemptCreate(BaseModel):
    """The body that records one completed run through a quiz set."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    mode: Literal["sequential", "random", "manual"] = Field(
        description="How the questions were chosen.",
    )
    question_count: int = Field(ge=1, description="How many questions the attempt covered.")
    correct_count: int = Field(ge=0, description="How many of them were answered correctly.")


class TutorAttemptOut(BaseModel):
    """One completed run through a quiz set."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: str = Field(description="The attempt's id.")
    mode: str = Field(description="How the questions were chosen.")
    question_count: int = Field(description="How many questions the attempt covered.")
    correct_count: int = Field(description="How many of them were answered correctly.")
    completed_at: str = Field(description="When the attempt was recorded, ISO 8601.")


class TutorQuizOut(BaseModel):
    """A quiz set, questions included."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: str = Field(description="The quiz set's id.")
    name: str = Field(description="The name it was given at import time.")
    created_at: str = Field(description="When it was built, ISO 8601.")
    questions: list[TutorQuestionOut] = Field(description="Its questions, in source order.")
    attempts: list[TutorAttemptOut] = Field(
        default_factory=list,
        description="Every completed run through it, oldest first.",
    )
    reference_folder: str = Field(
        default="",
        description="The hollow-relative folder its references were last resolved against, "
        "subfolders included; empty means the whole hollow.",
    )
    reference_separator: str = Field(
        default="",
        description="The literal that splits a reference label into several source names, "
        "empty when each label names a single source.",
    )


class TutorQuizSummaryOut(BaseModel):
    """A quiz set without its questions, for a list view."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: str = Field(description="The quiz set's id.")
    name: str = Field(description="The name it was given at import time.")
    created_at: str = Field(description="When it was built, ISO 8601.")
    question_count: int = Field(description="How many questions it holds.")
