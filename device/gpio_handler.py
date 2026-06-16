import time
from dataclasses import dataclass
from datetime import UTC, date, datetime

import RPi.GPIO as GPIO


@dataclass
class MoodCounts:
    good: int = 0
    neutral: int = 0
    bad: int = 0


class GpioHandler:
    def __init__(self, good_pin: int, neutral_pin: int, bad_pin: int, debounce_seconds: float = 0.25) -> None:
        self.good_pin = good_pin
        self.neutral_pin = neutral_pin
        self.bad_pin = bad_pin
        self.debounce_seconds = debounce_seconds

        self.total_counts = MoodCounts()
        self.hourly_counts = MoodCounts()
        # Separate daily display counter (local time). Used only for the Pi UI;
        # does NOT affect hourly upload aggregation. Resets automatically at midnight.
        self.daily_display_counts = MoodCounts()
        self.last_pressed = {
            "good": 0.0,
            "neutral": 0.0,
            "bad": 0.0,
        }
        self.current_hour_key = self._hour_key(datetime.now(UTC))
        self._current_day_key = self._day_key()
        # Track previous pin state for HIGH->LOW transition detection
        self._prev_state: dict[str, int] = {}
        # Queue of mood strings for per-press live-event uploads.
        # Each entry is one button press; drained by pop_live_events() in main.py.
        self._live_event_queue: list[str] = []

    def start(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.good_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.neutral_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.bad_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # Read initial states so first poll doesn't trigger a false press
        self._prev_state = {
            "good": GPIO.input(self.good_pin),
            "neutral": GPIO.input(self.neutral_pin),
            "bad": GPIO.input(self.bad_pin),
        }

    def update(self) -> None:
        """Poll pins and register presses on HIGH->LOW transitions."""
        pins = {
            "good": self.good_pin,
            "neutral": self.neutral_pin,
            "bad": self.bad_pin,
        }
        self._roll_hour_if_needed()
        self._roll_day_if_needed()
        for mood, pin in pins.items():
            current = GPIO.input(pin)
            if self._prev_state.get(mood, GPIO.HIGH) == GPIO.HIGH and current == GPIO.LOW:
                if self._can_press(mood):
                    setattr(self.total_counts, mood, getattr(self.total_counts, mood) + 1)
                    setattr(self.hourly_counts, mood, getattr(self.hourly_counts, mood) + 1)
                    setattr(self.daily_display_counts, mood, getattr(self.daily_display_counts, mood) + 1)
                    # Enqueue for live-event upload (one entry per press)
                    self._live_event_queue.append(mood)
            self._prev_state[mood] = current

    def stop(self) -> None:
        GPIO.cleanup()

    def get_counts(self) -> MoodCounts:
        self._roll_hour_if_needed()
        return MoodCounts(
            good=self.total_counts.good,
            neutral=self.total_counts.neutral,
            bad=self.total_counts.bad,
        )

    def get_hourly_counts(self) -> MoodCounts:
        self._roll_hour_if_needed()
        return MoodCounts(
            good=self.hourly_counts.good,
            neutral=self.hourly_counts.neutral,
            bad=self.hourly_counts.bad,
        )

    def get_daily_display_counts(self) -> MoodCounts:
        """Return today's display counts (local time). Auto-resets at midnight.

        These counts are for the Pi display only and are independent of the
        hourly upload aggregation counters.
        """
        self._roll_day_if_needed()
        return MoodCounts(
            good=self.daily_display_counts.good,
            neutral=self.daily_display_counts.neutral,
            bad=self.daily_display_counts.bad,
        )

    def clear_hourly_counts(self) -> None:
        self.hourly_counts = MoodCounts()
        self.current_hour_key = self._hour_key(datetime.now(UTC))

    def reset_daily_display_counts(self) -> None:
        """Manually reset the daily display counters (Pi display only, no server data affected)."""
        self.daily_display_counts = MoodCounts()
        self._current_day_key = self._day_key()

    def pop_live_events(self) -> list[str]:
        """Return and clear all pending live-event moods since the last call.

        Each entry is a mood string ('good', 'neutral', or 'bad') corresponding to
        one button press.  Callers (main.py) are expected to attempt a live-event
        upload for every returned entry and use save_failed_dict() for any that fail.
        """
        events, self._live_event_queue = self._live_event_queue, []
        return events

    def requeue_live_events(self, moods: list[str]) -> None:
        """Push drained live events back to the front of the queue."""
        if moods:
            self._live_event_queue = list(moods) + self._live_event_queue

    def _hour_key(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d-%H")

    def _day_key(self) -> str:
        return date.today().isoformat()

    def _roll_hour_if_needed(self) -> None:
        now_key = self._hour_key(datetime.now(UTC))
        if now_key != self.current_hour_key:
            self.hourly_counts = MoodCounts()
            self.current_hour_key = now_key

    def _roll_day_if_needed(self) -> None:
        today = self._day_key()
        if today != self._current_day_key:
            self.daily_display_counts = MoodCounts()
            self._current_day_key = today

    def _can_press(self, mood: str) -> bool:
        now = time.time()
        if now - self.last_pressed[mood] < self.debounce_seconds:
            return False
        self.last_pressed[mood] = now
        return True
