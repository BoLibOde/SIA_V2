"""Persistent local storage for daily mood counts (offline / fallback mode).

The file format is::

    {
        "date": "2026-07-08",
        "good": 5,
        "neutral": 3,
        "bad": 2,
        "last_updated": "2026-07-08T14:30:00+00:00"
    }

The file lives at ``device/tagesgesamt.json`` by default and is created
automatically when first written.  On each app start the stored date is
compared with today; a mismatch causes the counters to reset automatically.
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path

from device.models import MoodCounts


class OfflineStorage:
    """Read/write today's mood counts from a local JSON file.

    Usage
    -----
    * **Offline mode**: the file is the sole source of truth for daily counts.
    * **Online fallback**: used as a cache when the server is unreachable.

    All public methods are safe to call even when the file does not exist yet
    (e.g. on first boot).  Any I/O error is silently swallowed so that a
    storage hiccup never crashes the main app.
    """

    def __init__(self, data_file: str = "device/tagesgesamt.json") -> None:
        self.data_file = Path(data_file)
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_daily_counts(self) -> MoodCounts:
        """Return today's counts from disk, or zeros on any error / date mismatch."""
        data = self._read()
        if data is None:
            return MoodCounts()
        if data.get("date") != date.today().isoformat():
            # Stale data from a previous day – treat as a fresh start
            return MoodCounts()
        return MoodCounts(
            good=max(0, int(data.get("good", 0))),
            neutral=max(0, int(data.get("neutral", 0))),
            bad=max(0, int(data.get("bad", 0))),
        )

    def save_daily_counts(self, counts: MoodCounts) -> None:
        """Persist today's counts to disk, updating ``last_updated``."""
        self._write(
            {
                "date": date.today().isoformat(),
                "good": counts.good,
                "neutral": counts.neutral,
                "bad": counts.bad,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
        )

    def reset_on_new_day(self, current_counts: MoodCounts) -> tuple[bool, MoodCounts]:
        """Reset the counts if the calendar date has changed.

        Returns a ``(was_reset, new_counts)`` tuple.  When the date has *not*
        changed the original *current_counts* object is returned unchanged.
        When it *has* changed a fresh ``MoodCounts()`` is saved to disk and
        returned so the caller can swap its in-memory state.
        """
        data = self._read()
        today = date.today().isoformat()
        if data is not None and data.get("date") == today:
            return False, current_counts
        new_counts = MoodCounts()
        self.save_daily_counts(new_counts)
        return True, new_counts

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read(self) -> dict | None:
        if not self.data_file.exists():
            return None
        try:
            return json.loads(self.data_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _write(self, data: dict) -> None:
        try:
            self.data_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass
