import time
from dataclasses import dataclass
from datetime import datetime

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
        self.last_pressed = {
            "good": 0.0,
            "neutral": 0.0,
            "bad": 0.0,
        }
        self.current_hour_key = self._hour_key(datetime.utcnow())

    def start(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.good_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.neutral_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.bad_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.add_event_detect(self.good_pin, GPIO.FALLING, callback=self._good_pressed, bouncetime=200)
        GPIO.add_event_detect(self.neutral_pin, GPIO.FALLING, callback=self._neutral_pressed, bouncetime=200)
        GPIO.add_event_detect(self.bad_pin, GPIO.FALLING, callback=self._bad_pressed, bouncetime=200)

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

    def clear_hourly_counts(self) -> None:
        self.hourly_counts = MoodCounts()
        self.current_hour_key = self._hour_key(datetime.utcnow())

    def _hour_key(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d-%H")

    def _roll_hour_if_needed(self) -> None:
        now_key = self._hour_key(datetime.utcnow())
        if now_key != self.current_hour_key:
            self.hourly_counts = MoodCounts()
            self.current_hour_key = now_key

    def _can_press(self, mood: str) -> bool:
        now = time.time()
        if now - self.last_pressed[mood] < self.debounce_seconds:
            return False
        self.last_pressed[mood] = now
        return True

    def _good_pressed(self, channel: int) -> None:
        self._roll_hour_if_needed()
        if self._can_press("good"):
            self.total_counts.good += 1
            self.hourly_counts.good += 1

    def _neutral_pressed(self, channel: int) -> None:
        self._roll_hour_if_needed()
        if self._can_press("neutral"):
            self.total_counts.neutral += 1
            self.hourly_counts.neutral += 1

    def _bad_pressed(self, channel: int) -> None:
        self._roll_hour_if_needed()
        if self._can_press("bad"):
            self.total_counts.bad += 1
            self.hourly_counts.bad += 1
