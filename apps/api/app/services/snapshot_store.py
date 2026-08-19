from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredSnapshot:
    source_id: str
    sha256: str
    media_type: str
    retrieved_at: str
    content_path: Path
    metadata_path: Path


class SnapshotStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def put(
        self,
        *,
        source_id: str,
        body: bytes,
        media_type: str,
        retrieved_at: str,
    ) -> StoredSnapshot:
        digest = hashlib.sha256(body).hexdigest()
        source_root = self.root / source_id / digest
        source_root.mkdir(parents=True, exist_ok=True)
        content_path = source_root / "content.bin"
        metadata_path = source_root / "metadata.json"
        if not content_path.exists():
            tmp = source_root / ".content.tmp"
            tmp.write_bytes(body)
            tmp.replace(content_path)
        if not metadata_path.exists():
            metadata = {
                "source_id": source_id,
                "sha256": digest,
                "media_type": media_type,
                "first_retrieved_at": retrieved_at,
            }
            tmp_meta = source_root / ".metadata.tmp"
            tmp_meta.write_text(
                json.dumps(metadata, sort_keys=True, indent=2),
                encoding="utf-8",
            )
            tmp_meta.replace(metadata_path)
        return StoredSnapshot(
            source_id,
            digest,
            media_type,
            retrieved_at,
            content_path,
            metadata_path,
        )
