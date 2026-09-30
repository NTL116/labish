"""Local POSIX storage client skeleton."""

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StorageResult:
    success: bool
    path: str | None = None
    error: str | None = None


class LocalStorageClient:
    def __init__(self, base_dir: str = "/var/lib/labish/storage") -> None:
        self.base_dir = Path(base_dir)

    def write_bytes(self, relative_path: str, data: bytes) -> StorageResult:
        try:
            target = (self.base_dir / relative_path).resolve()
            if not target.is_relative_to(self.base_dir.resolve()):
                raise ValueError("Path escapes storage base directory")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return StorageResult(success=True, path=str(target))
        except Exception as exc:  # graceful degradation — never crash callers
            logger.warning("Storage write to %s failed: %s", relative_path, exc)
            return StorageResult(success=False, error=str(exc))
