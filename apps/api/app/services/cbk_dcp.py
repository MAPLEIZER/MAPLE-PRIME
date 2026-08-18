from __future__ import annotations

import re
from dataclasses import dataclass

_RECORD_START = re.compile(r"^\s*(\d+)\.\s+(.+?)\s*$")
_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
_PHONE = re.compile(r"(?:\+?\s*254(?:\s*\(0\))?|0)[\s-]*\d(?:[\s-]*\d){8,11}")
_FIELD = re.compile(
    r"^(Postal Address|Telephone(?: No)?|Email|E-mail address|Official Email|"
    r"Physical Address|Date Licensed)\s*:\s*(.*)$",
    re.I,
)
_HEADER_LINES = {
    "CENTRAL BANK OF KENYA",
    "DIRECTORY OF DIGITAL CREDIT PROVIDERS",
    "C2: CBK - Official",
}


@dataclass(frozen=True)
class DcpDirectoryRecord:
    sequence: int
    legal_name: str
    trading_name: str | None = None
    website: str | None = None
    emails: tuple[str, ...] = ()
    phones: tuple[str, ...] = ()
    postal_address: str | None = None
    physical_address: str | None = None
    licensed_date: str | None = None


def _skip_line(line: str) -> bool:
    stripped = line.strip()
    return (
        not stripped
        or stripped in _HEADER_LINES
        or stripped.upper().startswith("UPDATED ON ")
        or bool(re.fullmatch(r"\d+", stripped))
    )


def _normalise_phone(value: str) -> str:
    compact = re.sub(r"[\s()\-]", "", value)
    if compact.startswith("254"):
        compact = "+" + compact
    if compact.startswith("+2540"):
        compact = "+254" + compact[5:]
    if compact.startswith("0"):
        compact = "+254" + compact[1:]
    return compact


def _phones(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_normalise_phone(item) for item in _PHONE.findall(value)))


def _emails(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.lower() for item in _EMAIL.findall(value)))


def _split_name(value: str) -> tuple[str, str | None]:
    match = re.match(r"^(.*?)\s+trading\s+(?:under|as)\s+(.+)$", value, re.I)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return value.strip(), None


def _clean_date(value: str) -> str:
    # PDF text extractors sometimes append a page-footnote digit to the year.
    return re.sub(r"(\b20\d{2})\d{1,2}$", r"\1", value.strip())


def _legacy_record(sequence: int, line: str) -> DcpDirectoryRecord:
    parts = [part.strip() for part in line.split("|")]
    legal_name = parts[0]
    trading_name = parts[1] or None if len(parts) > 1 else None
    website = parts[2] or None if len(parts) > 2 else None
    tail = " | ".join(parts[3:]) if len(parts) > 3 else ""
    return DcpDirectoryRecord(
        sequence=sequence,
        legal_name=legal_name,
        trading_name=trading_name,
        website=website,
        emails=_emails(tail),
        phones=_phones(tail),
    )


def _parse_block(sequence: int, name_line: str, lines: list[str]) -> DcpDirectoryRecord:
    if "|" in name_line:
        return _legacy_record(sequence, name_line)

    legal_name, trading_name = _split_name(name_line)
    fields: dict[str, str] = {}
    current_key: str | None = None
    key_map = {
        "postal address": "postal",
        "telephone": "phone",
        "telephone no": "phone",
        "email": "email",
        "e-mail address": "email",
        "official email": "email",
        "physical address": "physical",
        "date licensed": "licensed",
    }

    for line in lines:
        if _skip_line(line):
            continue
        match = _FIELD.match(line.strip())
        if match:
            current_key = key_map[match.group(1).lower()]
            value = match.group(2).strip()
            fields[current_key] = (
                f"{fields[current_key]} {value}".strip()
                if current_key in fields
                else value
            )
        elif current_key:
            fields[current_key] = f"{fields[current_key]} {line.strip()}".strip()

    return DcpDirectoryRecord(
        sequence=sequence,
        legal_name=legal_name,
        trading_name=trading_name,
        emails=_emails(fields.get("email", "")),
        phones=_phones(fields.get("phone", "")),
        postal_address=fields.get("postal") or None,
        physical_address=fields.get("physical") or None,
        licensed_date=_clean_date(fields["licensed"]) if fields.get("licensed") else None,
    )


def parse_directory_text(text: str) -> list[DcpDirectoryRecord]:
    blocks: list[tuple[int, str, list[str]]] = []
    current: tuple[int, str, list[str]] | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        start = _RECORD_START.match(line)
        if start:
            if current:
                blocks.append(current)
            current = (int(start.group(1)), start.group(2).strip(), [])
            continue
        if current and not _skip_line(line):
            current[2].append(line)
    if current:
        blocks.append(current)

    records = [_parse_block(*block) for block in blocks]
    if not records:
        raise ValueError("no DCP records were parsed from the supplied text")
    return records
