"""The façade the rest of the project holds.

``TutorConnector`` stages an uploaded spreadsheet, turns it into a quiz set
once its columns are mapped, and persists quiz sets the same way the settings
connector persists its toggles. It knows nothing about the hollow: a
reference is resolved by whoever calls ``commit_import``, through the
callback it is handed, so this package stays unaware that notes exist.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from .parsing import parse_upload
from .types import (
    ImportNotFound,
    InvalidAttempt,
    InvalidMapping,
    ParsedTable,
    QuizAttempt,
    QuizNotFound,
    QuizQuestion,
    QuizSet,
    QuizSummary,
)

logger = logging.getLogger(__name__)

MAX_PENDING_IMPORTS = 20
VALID_MODES = ("sequential", "random", "manual")


def _read_reference_paths(question: dict) -> tuple[str, ...]:
    """A persisted question's resolved paths, the old single-path field included.

    Data written before multi-reference support held one ``reference_path``
    (or None); newer data holds a ``reference_paths`` list.
    """
    if "reference_paths" in question:
        return tuple(question["reference_paths"])
    legacy = question.get("reference_path")
    return (legacy,) if legacy else ()


def _split_reference_label(label: str, separator: str) -> list[str]:
    """A reference label split into its source names.

    Args:
        label: The reference label, as it was in the source column.
        separator: The literal that separates several source names within
            one label. Empty treats the whole label as a single source.

    Returns:
        Each non-blank part, trimmed -- a single-element list holding the
        whole label when ``separator`` is empty or does not occur in it.
    """
    if not separator:
        return [label] if label else []
    return [part.strip() for part in label.split(separator) if part.strip()]


class TutorConnector:
    """Staged imports and persisted quiz sets for the exam tutor."""

    def __init__(self, path: Path) -> None:
        """Open the connector on its data file, reading what it holds.

        Args:
            path: Where quiz sets are persisted. Created on first write.
        """
        self._path = path
        self._lock = threading.Lock()
        self._pending: OrderedDict[str, ParsedTable] = OrderedDict()
        self._quizzes: dict[str, QuizSet] = self._read()
        logger.info("Tutor data opened at %s", self._path)

    def _read(self) -> dict[str, QuizSet]:
        """The persisted quiz sets, empty when there is no file yet."""
        if not self._path.is_file():
            return {}
        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("Cannot read %s, starting empty: %s", self._path, error)
            return {}
        quizzes: dict[str, QuizSet] = {}
        for quiz_id, raw in document.get("quizzes", {}).items():
            try:
                quizzes[quiz_id] = QuizSet(
                    id=raw["id"],
                    name=raw["name"],
                    created_at=raw["created_at"],
                    questions=tuple(
                        QuizQuestion(
                            id=question["id"],
                            question=question["question"],
                            answers=tuple(question["answers"]),
                            correct_indices=tuple(
                                question["correct_indices"]
                                if "correct_indices" in question
                                # Read as it was written before multi-answer support.
                                else [question["correct_index"]]
                            ),
                            reference=question.get("reference", ""),
                            reference_paths=_read_reference_paths(question),
                        )
                        for question in raw.get("questions", [])
                    ),
                    attempts=tuple(
                        QuizAttempt(
                            id=attempt["id"],
                            mode=attempt["mode"],
                            question_count=attempt["question_count"],
                            correct_count=attempt["correct_count"],
                            completed_at=attempt["completed_at"],
                        )
                        for attempt in raw.get("attempts", [])
                    ),
                    reference_folder=raw.get("reference_folder", ""),
                    reference_separator=raw.get("reference_separator", ""),
                )
            except (KeyError, TypeError) as error:
                logger.warning("Ignoring a malformed quiz set in %s: %s", self._path, error)
        return quizzes

    def _write(self) -> None:
        """Persist the in-memory quiz sets, atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        document = {"quizzes": {quiz_id: asdict(quiz) for quiz_id, quiz in self._quizzes.items()}}
        tmp_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        tmp_path.write_text(json.dumps(document, indent=2), encoding="utf-8")
        os.replace(tmp_path, self._path)

    def stage_import(self, filename: str, content: bytes) -> ParsedTable:
        """Parse an uploaded spreadsheet and hold it for column mapping.

        Args:
            filename: The name the upload arrived with.
            content: The bytes of the upload.

        Returns:
            The staged table, keyed by a fresh id.

        Raises:
            UnsupportedFile: The upload is neither a ``.csv`` nor a ``.xlsx``,
                or it cannot be parsed.
        """
        table = parse_upload(filename, content)
        with self._lock:
            self._pending[table.id] = table
            while len(self._pending) > MAX_PENDING_IMPORTS:
                self._pending.popitem(last=False)
        return table

    def get_pending(self, import_id: str) -> ParsedTable:
        """The staged table an import id was given.

        Raises:
            ImportNotFound: No staged import carries this id -- it was never
                uploaded, was already committed, or aged out behind newer ones.
        """
        with self._lock:
            table = self._pending.get(import_id)
        if table is None:
            raise ImportNotFound(f"No staged import: {import_id}")
        return table

    def commit_import(
        self,
        import_id: str,
        *,
        name: str,
        question_column: str,
        answer_columns: tuple[str, ...],
        correct_column: str,
        reference_column: str | None,
        reference_separator: str = "",
        resolve_reference: Callable[[str], str | None],
    ) -> QuizSet:
        """Build and persist a quiz set out of a staged import and a column mapping.

        Args:
            import_id: The staged import to build from.
            name: The name to give the quiz set. Falls back to the uploaded
                file's name when blank.
            question_column: The column holding each question's text.
            answer_columns: The columns holding each answer, in display order.
            correct_column: The column naming each row's correct answer, or
                more than one -- matched, case- and whitespace-insensitively,
                against that row's answers; against a letter (A, B, C, ...)
                or a 1-based number naming one by position; against several
                such letters run together ("CDE") or separated by a comma,
                slash, "and" or "e" ("C, D", "B/D"); or, once split that way,
                against several answers' own text.
            reference_column: The column holding a reference note's name, or
                None when the quiz has no references.
            reference_separator: The literal that splits a reference label
                into several source names ("A.md; B.md"). Empty treats each
                label as naming a single source.
            resolve_reference: Called with each non-empty reference label
                part to resolve it to a hollow-relative path, or None when
                nothing matches.

        Returns:
            The quiz set that was persisted.

        Raises:
            ImportNotFound: No staged import carries ``import_id``.
            InvalidMapping: A named column is not in the table, fewer than two
                answer columns were given, or a row's correct-answer value or
                answers could not be resolved.
        """
        table = self.get_pending(import_id)
        columns = set(table.columns)
        if len(answer_columns) < 2:
            raise InvalidMapping("A question needs at least two answer columns")
        for column in (question_column, correct_column, *answer_columns):
            if column not in columns:
                raise InvalidMapping(f"'{column}' is not a column of the uploaded file")
        if reference_column is not None and reference_column not in columns:
            raise InvalidMapping(f"'{reference_column}' is not a column of the uploaded file")

        index_of = {column: position for position, column in enumerate(table.columns)}
        questions: list[QuizQuestion] = []
        for row_number, row in enumerate(table.rows, start=2):
            question_text = row[index_of[question_column]]
            if not question_text:
                continue
            answers = tuple(
                value for value in (row[index_of[column]] for column in answer_columns) if value
            )
            if len(answers) < 2:
                raise InvalidMapping(f"Row {row_number} does not have two answers")
            correct_raw = row[index_of[correct_column]]
            correct_indices = _match_answers(answers, correct_raw)
            if correct_indices is None:
                raise InvalidMapping(
                    f"Row {row_number}: the correct answer '{correct_raw}' matches none of "
                    "its answers"
                )
            reference_label = row[index_of[reference_column]] if reference_column else ""
            parts = _split_reference_label(reference_label, reference_separator)
            reference_paths = tuple(
                path for part in parts if (path := resolve_reference(part)) is not None
            )
            questions.append(
                QuizQuestion(
                    id=uuid.uuid4().hex,
                    question=question_text,
                    answers=answers,
                    correct_indices=correct_indices,
                    reference=reference_label,
                    reference_paths=reference_paths,
                )
            )
        if not questions:
            raise InvalidMapping("The uploaded file has no usable rows")

        quiz = QuizSet(
            id=uuid.uuid4().hex,
            name=name.strip() or table.filename,
            created_at=datetime.now(UTC).isoformat(),
            questions=tuple(questions),
            reference_separator=reference_separator.strip(),
        )
        with self._lock:
            self._quizzes[quiz.id] = quiz
            self._write()
            self._pending.pop(import_id, None)
        return quiz

    def list_quizzes(self) -> tuple[QuizSummary, ...]:
        """Every persisted quiz set, without its questions, newest first."""
        with self._lock:
            quizzes = sorted(self._quizzes.values(), key=lambda quiz: quiz.created_at, reverse=True)
        return tuple(
            QuizSummary(
                id=quiz.id,
                name=quiz.name,
                created_at=quiz.created_at,
                question_count=len(quiz.questions),
            )
            for quiz in quizzes
        )

    def get_quiz(self, quiz_id: str) -> QuizSet:
        """One persisted quiz set, questions included.

        Raises:
            QuizNotFound: No quiz set carries this id.
        """
        with self._lock:
            quiz = self._quizzes.get(quiz_id)
        if quiz is None:
            raise QuizNotFound(f"No such quiz: {quiz_id}")
        return quiz

    def rename_quiz(self, quiz_id: str, name: str) -> QuizSet:
        """Give a quiz set a new name.

        Args:
            quiz_id: The quiz set to rename.
            name: Its new name.

        Returns:
            The quiz set, questions and attempts included, under its new name.

        Raises:
            QuizNotFound: No quiz set carries this id.
            InvalidMapping: The name is blank once trimmed.
        """
        clean = name.strip()
        if not clean:
            raise InvalidMapping("The name cannot be blank")
        with self._lock:
            quiz = self._quizzes.get(quiz_id)
            if quiz is None:
                raise QuizNotFound(f"No such quiz: {quiz_id}")
            renamed = replace(quiz, name=clean)
            self._quizzes[quiz_id] = renamed
            self._write()
        return renamed

    def set_reference_folder(
        self,
        quiz_id: str,
        folder: str,
        resolve_reference: Callable[[str], str | None],
    ) -> QuizSet:
        """Re-resolve every question's reference within one folder of the hollow.

        Each question keeps the reference label it was imported with; only
        the path it resolves to is refreshed, against the new folder.

        Args:
            quiz_id: The quiz set to update.
            folder: The hollow-relative folder to search, subfolders included.
                Empty searches the whole hollow.
            resolve_reference: Called with each non-empty reference label,
                already scoped to ``folder``, returning the path it resolves
                to, or None when nothing in scope matches.

        Returns:
            The quiz set, its references refreshed and its folder remembered.

        Raises:
            QuizNotFound: No quiz set carries this id.
        """
        clean_folder = folder.strip().strip("/")
        with self._lock:
            quiz = self._quizzes.get(quiz_id)
            if quiz is None:
                raise QuizNotFound(f"No such quiz: {quiz_id}")
            resolved_questions = tuple(
                replace(
                    question,
                    reference_paths=tuple(
                        path
                        for part in _split_reference_label(question.reference, quiz.reference_separator)
                        if (path := resolve_reference(part)) is not None
                    ),
                )
                for question in quiz.questions
            )
            updated = replace(quiz, questions=resolved_questions, reference_folder=clean_folder)
            self._quizzes[quiz_id] = updated
            self._write()
        return updated

    def record_attempt(
        self,
        quiz_id: str,
        *,
        mode: str,
        question_count: int,
        correct_count: int,
    ) -> QuizSet:
        """Record one completed run through a quiz set, for its statistics.

        Args:
            quiz_id: The quiz set the attempt was against.
            mode: How the questions were chosen: "sequential", "random", or
                "manual" -- the three modes the detail page offers.
            question_count: How many questions the attempt covered.
            correct_count: How many of them were answered correctly.

        Returns:
            The quiz set, with the new attempt appended.

        Raises:
            QuizNotFound: No quiz set carries this id.
            InvalidAttempt: ``mode`` is not one of the three offered, or the
                counts do not describe a real result.
        """
        if mode not in VALID_MODES:
            raise InvalidAttempt(f"'{mode}' is not a mode the tutor offers")
        if question_count < 1 or not (0 <= correct_count <= question_count):
            raise InvalidAttempt("The attempt's counts do not describe a real result")
        attempt = QuizAttempt(
            id=uuid.uuid4().hex,
            mode=mode,
            question_count=question_count,
            correct_count=correct_count,
            completed_at=datetime.now(UTC).isoformat(),
        )
        with self._lock:
            quiz = self._quizzes.get(quiz_id)
            if quiz is None:
                raise QuizNotFound(f"No such quiz: {quiz_id}")
            updated = replace(quiz, attempts=(*quiz.attempts, attempt))
            self._quizzes[quiz_id] = updated
            self._write()
        return updated

    def delete_quiz(self, quiz_id: str) -> None:
        """Delete a quiz set.

        Raises:
            QuizNotFound: No quiz set carries this id.
        """
        with self._lock:
            if quiz_id not in self._quizzes:
                raise QuizNotFound(f"No such quiz: {quiz_id}")
            del self._quizzes[quiz_id]
            self._write()


_SEPARATORS = re.compile(r"[,;/&+]| and | e ", re.IGNORECASE)


def _match_one(answers: tuple[str, ...], token: str) -> int | None:
    """The index into ``answers`` that a single token names.

    A row usually repeats the correct answer's own text; some spreadsheets
    instead name it by a letter or a 1-based position, so both are accepted
    once an exact match fails.
    """
    wanted = token.strip().lower()
    if not wanted:
        return None
    for index, answer in enumerate(answers):
        if answer.strip().lower() == wanted:
            return index
    if len(wanted) == 1 and wanted.isalpha():
        letter_index = ord(wanted) - ord("a")
        if 0 <= letter_index < len(answers):
            return letter_index
    if wanted.isdigit():
        number_index = int(wanted) - 1
        if 0 <= number_index < len(answers):
            return number_index
    return None


def _match_answers(answers: tuple[str, ...], correct_raw: str) -> tuple[int, ...] | None:
    """The indices into ``answers`` that ``correct_raw`` names, one or several.

    Tried in order: the whole value as a single token (its own text, a
    letter, or a position -- the ordinary, single-answer case); several
    tokens split on a comma, a slash, or the like ("B, D", "B/D"); and,
    lastly, several answer letters run together with nothing between them
    ("CDE"). None of these are attempted for an empty value.
    """
    raw = correct_raw.strip()
    if not raw:
        return None

    single = _match_one(answers, raw)
    if single is not None:
        return (single,)

    parts = [part for part in _SEPARATORS.split(raw) if part.strip()]
    if len(parts) > 1:
        indices = [_match_one(answers, part) for part in parts]
        if all(index is not None for index in indices):
            return tuple(sorted(dict.fromkeys(index for index in indices if index is not None)))

    if len(raw) > 1 and raw.isalpha() and raw.isascii():
        letters = [ord(char.lower()) - ord("a") for char in raw]
        if len(set(letters)) == len(letters) and all(0 <= index < len(answers) for index in letters):
            return tuple(sorted(letters))

    return None
