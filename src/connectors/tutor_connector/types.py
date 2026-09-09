"""What the tutor connector hands out, and what it raises."""

from __future__ import annotations

from dataclasses import dataclass


class TutorError(Exception):
    """Base of everything the tutor connector raises."""


class ImportNotFound(TutorError):
    """No staged import carries the requested id."""


class InvalidMapping(TutorError):
    """The chosen columns cannot build a quiz out of the staged table."""


class QuizNotFound(TutorError):
    """No quiz set carries the requested id."""


class UnsupportedFile(TutorError):
    """The upload is neither a .csv nor a .xlsx file, or it cannot be parsed."""


class InvalidAttempt(TutorError):
    """The attempt being recorded does not describe a real result."""


@dataclass(frozen=True, slots=True)
class ParsedTable:
    """A spreadsheet staged for column mapping, before it becomes a quiz.

    Attributes:
        id: The id this staged import is held under.
        filename: The name the upload arrived with.
        columns: The header row.
        rows: Every data row, one tuple of cell strings per row, the same
            length as ``columns``. A row that was entirely blank is dropped.
    """

    id: str
    filename: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class QuizQuestion:
    """One question of a quiz set.

    Attributes:
        id: The question's id, stable within its quiz set.
        question: The question text.
        answers: The possible answers, in the order the quiz shows them.
        correct_indices: The indices into ``answers`` that are correct -- one
            for an ordinary question, more than one for a question the
            correct-answer column named several answers for.
        reference: The reference label as it was in the source column, empty
            when the row had none. May name more than one source, joined by
            the quiz set's ``reference_separator``.
        reference_paths: The hollow-relative paths each part of ``reference``
            resolved to, in order -- a part that matched nothing is left out,
            so this can be shorter than the number of parts, empty when none
            of them matched.
    """

    id: str
    question: str
    answers: tuple[str, ...]
    correct_indices: tuple[int, ...]
    reference: str = ""
    reference_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QuizAttempt:
    """One completed run through a quiz set, kept for its statistics.

    Attributes:
        id: The attempt's id.
        mode: How its questions were chosen: "sequential", "random", or "manual".
        question_count: How many questions the attempt covered.
        correct_count: How many of them were answered correctly.
        completed_at: When the attempt was recorded, ISO 8601.
    """

    id: str
    mode: str
    question_count: int
    correct_count: int
    completed_at: str


@dataclass(frozen=True, slots=True)
class QuizSet:
    """A deck of questions built from one imported spreadsheet.

    Attributes:
        id: The quiz set's id.
        name: The name it was given at import time.
        created_at: When it was built, ISO 8601.
        questions: Its questions, in source order.
        attempts: Every completed run through it, oldest first.
        reference_folder: The hollow-relative folder its references were last
            resolved against, subfolders included; empty means the whole hollow.
        reference_separator: The literal that splits a reference label into
            several source names, empty when each label names a single source.
    """

    id: str
    name: str
    created_at: str
    questions: tuple[QuizQuestion, ...] = ()
    attempts: tuple[QuizAttempt, ...] = ()
    reference_folder: str = ""
    reference_separator: str = ""


@dataclass(frozen=True, slots=True)
class QuizSummary:
    """A quiz set without its questions, for a list view.

    Attributes:
        id: The quiz set's id.
        name: The name it was given at import time.
        created_at: When it was built, ISO 8601.
        question_count: How many questions it holds.
    """

    id: str
    name: str
    created_at: str
    question_count: int
