"""
Disk-backed cache for fetched web pages.

Cache layout: <cache_dir>/<first-16-chars-of-sha256-hex>.json
Each file is a JSON-encoded dict with raw bytes stored as base64.

Atomic writes: content is written to a .tmp file then renamed.
Cache expiry is not implemented in RC3.
No arbitrary deserialization: only JSON is used.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import pathlib

LOGGER = logging.getLogger(__name__)


class WebCache:
    """Simple disk-backed cache for fetched web page content.

    Cache path is caller-supplied. No hidden global cache.
    JSON format only — no pickle.

    Keys are the first 16 hex chars of SHA-256(url). Collisions are
    negligible in practice for a single-session cache.
    """

    def __init__(self, cache_dir: str | pathlib.Path) -> None:
        self._dir = pathlib.Path(cache_dir)

    def _key_path(self, url: str) -> pathlib.Path:
        key = hashlib.sha256(url.encode()).hexdigest()[:16]
        return self._dir / f"{key}.json"

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def get(self, url: str) -> dict[str, object] | None:
        """Return cached data for url, or None on miss or error."""
        path = self._key_path(url)
        if not path.exists():
            return None
        try:
            data: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
            # Decode base64 content field if present
            if "content_b64" in data:
                raw_b64 = data.pop("content_b64")
                data["content"] = base64.b64decode(str(raw_b64))
            return data
        except Exception as exc:
            LOGGER.warning("Failed to read cache file %s: %s", path, exc)
            return None

    def set(self, url: str, data: dict[str, object]) -> None:
        """Persist data for url. Silently ignores write errors."""
        try:
            self._ensure_dir()
            path = self._key_path(url)
            tmp_path = path.with_suffix(".tmp")

            # Encode bytes fields as base64 for JSON safety
            serializable: dict[str, object] = {}
            for k, v in data.items():
                if isinstance(v, bytes):
                    serializable[f"{k}_b64"] = base64.b64encode(v).decode("ascii")
                else:
                    serializable[k] = v

            tmp_path.write_text(
                json.dumps(serializable, ensure_ascii=False), encoding="utf-8"
            )
            tmp_path.replace(path)
        except Exception as exc:
            LOGGER.warning("Failed to write cache entry for %s: %s", url, exc)

    def invalidate(self, url: str) -> bool:
        """Delete the cache entry for url. Returns True if a file was removed."""
        path = self._key_path(url)
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception as exc:
                LOGGER.warning("Failed to delete cache file %s: %s", path, exc)
        return False
