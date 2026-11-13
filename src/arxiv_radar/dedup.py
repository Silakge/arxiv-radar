"""Seen-paper store so repeated runs only surface genuinely new papers."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, timedelta

PRUNE_DAYS = 90


class SeenStore:
    """A tiny JSON file mapping arXiv ids -> date first seen.

    The file lives inside the output directory, which means committing the
    output folder in GitHub Actions also persists the dedup state for free.
    """

    def __init__(self, path: str):
        self.path = path
        self._seen: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            # A corrupted state file should never block a fresh digest.
            data = None
        papers = data.get("papers") if isinstance(data, dict) else None
        if not isinstance(papers, dict):
            papers = {}
        self._seen = {key: value for key, value in papers.items() if isinstance(value, str)}

    def is_seen(self, arxiv_id: str) -> bool:
        return arxiv_id in self._seen

    def filter_unseen(self, ids: list[str]) -> list[str]:
        return [i for i in ids if not self.is_seen(i)]

    def mark(self, arxiv_ids: list[str], when: date | None = None) -> None:
        when = when or date.today()
        for arxiv_id in arxiv_ids:
            self._seen.setdefault(arxiv_id, when.isoformat())

    def prune(self, keep_days: int = PRUNE_DAYS) -> int:
        """Drop entries older than keep_days. Returns the number removed."""
        cutoff = (date.today() - timedelta(days=keep_days)).isoformat()
        stale = [k for k, v in self._seen.items() if v < cutoff]
        for key in stale:
            del self._seen[key]
        return len(stale)

    def save(self) -> None:
        """Persist atomically (tmp file + os.replace)."""
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        payload = {"papers": dict(sorted(self._seen.items()))}
        fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=1, ensure_ascii=False)
            os.replace(tmp_path, self.path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def __len__(self) -> int:
        return len(self._seen)
