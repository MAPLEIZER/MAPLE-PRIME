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


class OdpcRegistryAccessRestricted(ValueError):
    """Raised when ODPC returns an access/challenge page instead of registry data."""


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
    value = value.replace("\ufeff", "").replace("\xa0", " ").strip().lower()
    value = re.sub(r"[^a-z0-9#]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


_HEADER_ALIASES = {
    "#": "sequence",
    "no": "sequence",
    "number": "sequence",
    "name": "name",
    "organisation name": "name",
    "organization name": "name",
    "data handler name": "name",
    "data handler type": "handler_type",
    "handler type": "handler_type",
    "registration number": "registration_number",
    "registration no": "registration_number",
    "registration": "registration_number",
    "county": "county",
    "country": "country",
    "status": "status",
    "status as at": "status_as_at",
    "status date": "status_as_at",
}
_REQUIRED = {"name", "handler_type", "registration_number", "status"}
_REGISTRATION_RE = re.compile(r"^INST-[A-Z0-9]+$", re.IGNORECASE)
_ACCESS_CHALLENGE_MARKERS = (
    "verify you are human",
    "checking your browser",
    "enable javascript and cookies",
    "cf-chl-",
    "captcha",
    "access denied",
)


def _positions(row: list[str]) -> dict[str, int]:
    positions: dict[str, int] = {}
    for index, value in enumerate(row):
        canonical = _HEADER_ALIASES.get(_header(value))
        if canonical is not None and canonical not in positions:
            positions[canonical] = index
    return positions


def _find_header(table: list[list[str]]) -> tuple[int, dict[str, int]] | None:
    # Publishing plugins commonly add a title/merged row before the actual
    # column headings. Search a bounded prefix instead of assuming row zero.
    for index, row in enumerate(table[:12]):
        positions = _positions(row)
        if _REQUIRED.issubset(positions):
            return index, positions
    return None


def _cell(row: list[str], positions: dict[str, int], key: str) -> str:
    index = positions.get(key)
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def parse_registered_handlers_html(html: str) -> list[OdpcHandlerRecord]:
    parser = _TableParser()
    parser.feed(html)

    for table in parser.tables:
        located = _find_header(table)
        if located is None:
            continue
        header_index, positions = located
        records: list[OdpcHandlerRecord] = []
        for row in table[header_index + 1 :]:
            # Some table plugins repeat the header in long tables/pages.
            if _REQUIRED.issubset(_positions(row)):
                continue

            name = _cell(row, positions, "name")
            handler_type = _cell(row, positions, "handler_type")
            registration_number = _cell(row, positions, "registration_number")
            status = _cell(row, positions, "status")
            if not name and not handler_type and not registration_number and not status:
                continue
            if not name or not handler_type or not status:
                continue
            if not _REGISTRATION_RE.fullmatch(registration_number):
                continue

            sequence_raw = _cell(row, positions, "sequence")
            records.append(
                OdpcHandlerRecord(
                    sequence=int(sequence_raw) if sequence_raw.isdigit() else None,
                    name=name,
                    handler_type=handler_type,
                    registration_number=registration_number,
                    county=_cell(row, positions, "county") or None,
                    country=_cell(row, positions, "country") or None,
                    status=status,
                    status_as_at=_cell(row, positions, "status_as_at") or None,
                )
            )
        if records:
            return records

    lowered = html.lower()
    if any(marker in lowered for marker in _ACCESS_CHALLENGE_MARKERS):
        raise OdpcRegistryAccessRestricted("ODPC returned an access/challenge page")
    raise ValueError("ODPC registry table was not found or did not match the expected schema")
