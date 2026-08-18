from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass(frozen=True)
class OdpcHandlerRecord:
    sequence: int | None
    name: str
    handler_type: str
    registration_number: str
    county: str | None
    country: str | None
    status: str
    status_as_at: str | None


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag == "table" and self._table is None:
            self._table = []
        elif self._table is not None and tag == "tr":
            self._row = []
        elif self._row is not None and tag in {"td", "th"}:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def _header(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def parse_registered_handlers_html(html: str) -> list[OdpcHandlerRecord]:
    parser = _TableParser()
    parser.feed(html)
    required = {"name", "data handler type", "registration number", "status"}

    for table in parser.tables:
        if not table:
            continue
        headers = [_header(value) for value in table[0]]
        if not required.issubset(headers):
            continue
        positions = {header: index for index, header in enumerate(headers)}
        records: list[OdpcHandlerRecord] = []
        for row in table[1:]:
            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))
            sequence_raw = row[positions.get("#", 0)].strip()
            records.append(
                OdpcHandlerRecord(
                    sequence=int(sequence_raw) if sequence_raw.isdigit() else None,
                    name=row[positions["name"]].strip(),
                    handler_type=row[positions["data handler type"]].strip(),
                    registration_number=row[positions["registration number"]].strip(),
                    county=row[positions["county"]].strip() or None if "county" in positions else None,
                    country=row[positions["country"]].strip() or None if "country" in positions else None,
                    status=row[positions["status"]].strip(),
                    status_as_at=(row[positions["status as at"]].strip() or None)
                    if "status as at" in positions
                    else None,
                )
            )
        if records:
            return records
    raise ValueError("ODPC registry table was not found or did not match the expected schema")
