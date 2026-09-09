"""Turning an uploaded ``.csv`` or ``.xlsx`` into a ``ParsedTable``.

Nothing here knows about column mapping or quizzes -- it only turns bytes
into a header and rows of text, the same shape whichever format they came in.
"""

from __future__ import annotations

import csv
import io
import uuid
import zipfile
from collections.abc import Iterable, Iterator

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from .types import ParsedTable, UnsupportedFile

Row = tuple[str, ...]


def parse_upload(filename: str, content: bytes) -> ParsedTable:
    """Parse an uploaded spreadsheet into a header and its rows of text.

    Args:
        filename: The name the upload arrived with; only its extension is used.
        content: The bytes of the upload.

    Returns:
        A freshly staged table, keyed by a new id.

    Raises:
        UnsupportedFile: The extension is neither ``.csv`` nor ``.xlsx``, the
            file has no header row, or it cannot be parsed at all.
    """
    lowered = filename.lower()
    if lowered.endswith(".csv"):
        columns, rows = _split(_read_csv(content))
    elif lowered.endswith(".xlsx"):
        columns, rows = _split(_read_xlsx(content))
    else:
        raise UnsupportedFile(f"'{filename}' is neither a .csv nor a .xlsx file")
    if not columns:
        raise UnsupportedFile("The file has no header row")
    return ParsedTable(id=uuid.uuid4().hex, filename=filename, columns=columns, rows=rows)


def _read_csv(content: bytes) -> Iterator[Iterable[object]]:
    """Read a ``.csv``, sniffing its delimiter with a comma as the fallback."""
    text = content.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return csv.reader(io.StringIO(text), dialect)


def _read_xlsx(content: bytes) -> Iterator[Iterable[object]]:
    """Read the first sheet of a ``.xlsx`` workbook."""
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except (InvalidFileException, zipfile.BadZipFile, KeyError, OSError) as error:
        raise UnsupportedFile(f"That is not a valid .xlsx file: {error}") from error
    sheet = workbook.active
    if sheet is None:
        raise UnsupportedFile("The workbook has no sheet")
    return sheet.iter_rows(values_only=True)


def _split(source: Iterator[Iterable[object]]) -> tuple[Row, tuple[Row, ...]]:
    """Split raw rows into a header and its data rows.

    A row shorter than the header is padded with empty cells; a longer one is
    cut to the header's width. A row that is entirely blank is dropped.
    """
    try:
        header = _row(next(source))
    except StopIteration:
        return (), ()
    width = len(header)
    rows: list[Row] = []
    for raw in source:
        cells = _row(raw)
        if len(cells) < width:
            cells = cells + ("",) * (width - len(cells))
        else:
            cells = cells[:width]
        if any(cells):
            rows.append(cells)
    return header, tuple(rows)


def _row(raw: Iterable[object]) -> Row:
    """One raw row, coerced to trimmed strings, ``None`` becoming empty."""
    return tuple("" if cell is None else str(cell).strip() for cell in raw)
