"""The only code in the project that turns a spreadsheet into a quiz.

``TutorConnector`` is the whole surface; everything else here is what stands
behind it.
"""

from .connector import TutorConnector
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
    TutorError,
    UnsupportedFile,
)

__all__ = [
    "ImportNotFound",
    "InvalidAttempt",
    "InvalidMapping",
    "ParsedTable",
    "QuizAttempt",
    "QuizNotFound",
    "QuizQuestion",
    "QuizSet",
    "QuizSummary",
    "TutorConnector",
    "TutorError",
    "UnsupportedFile",
]
