from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DcpDirectoryRecord:
    legal_name: str
    trading_name: str | None
    website: str | None
    emails: tuple[str, ...]
    phones: tuple[str, ...]


_ROW = re.compile(r"^\s*\d+[.)]?\s*(.+)$")
_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
_PHONE = re.compile(r"\+?254\d{9}|0\d{9}")


def parse_directory_text(text: str) -> list[DcpDirectoryRecord]:
    records: list[DcpDirectoryRecord] = []
    for raw_line in text.splitlines():
        match = _ROW.match(raw_line)
        if not match:
            continue
        parts = [part.strip() for part in match.group(1).split("|")]
        if not parts or not parts[0]:
            continue
        legal_name = parts[0]
        trading_name = (parts[1] or None) if len(parts) > 1 else None
        website = (parts[2] or None) if len(parts) > 2 else None
        tail = " | ".join(parts[3:]) if len(parts) > 3 else ""
        emails = tuple(dict.fromkeys(_EMAIL.findall(tail)))
        phones = tuple(dict.fromkeys(_PHONE.findall(tail)))
        records.append(
            DcpDirectoryRecord(
                legal_name=legal_name,
                trading_name=trading_name,
                website=website,
                emails=emails,
                phones=phones,
            )
        )
    if not records:
        raise ValueError("no DCP records were parsed from the supplied text")
    return records
