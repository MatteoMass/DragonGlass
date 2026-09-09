"""The only code in the project that touches the filesystem.

``HollowConnector`` is the whole surface; everything else here is what stands
behind it.
"""

from .connector import HollowConnector
from .types import (
    Entry,
    EntryAlreadyExists,
    EntryKind,
    EntryNotFound,
    ImportResult,
    IndexedNote,
    InvalidMove,
    InvalidName,
    InvalidPath,
    Note,
    NoteIndex,
    NotANote,
    UploadedImage,
    HollowConfig,
    HollowError,
)

__all__ = [
    "Entry",
    "EntryAlreadyExists",
    "EntryKind",
    "EntryNotFound",
    "ImportResult",
    "IndexedNote",
    "InvalidMove",
    "InvalidName",
    "InvalidPath",
    "NotANote",
    "Note",
    "NoteIndex",
    "UploadedImage",
    "HollowConfig",
    "HollowConnector",
    "HollowError",
]
