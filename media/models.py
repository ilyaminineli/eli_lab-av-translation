from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class MediaAsset:
    id: str
    path: str
    collection_id: str
    name: str
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    codec: str | None = None
    thumbnail_path: str | None = None
    status: str = "ready"
    file_size: int = 0
    modified_at: float = 0.0

    @property
    def exists(self) -> bool:
        return Path(self.path).is_file()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: Any) -> MediaAsset:
        return cls(
            id=row["id"],
            path=row["path"],
            collection_id=row["collection_id"],
            name=row["name"],
            duration=row["duration"],
            width=row["width"],
            height=row["height"],
            fps=row["fps"],
            codec=row["codec"],
            thumbnail_path=row["thumbnail_path"],
            status=row["status"],
            file_size=row["file_size"],
            modified_at=row["modified_at"],
        )
