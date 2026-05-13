import time
from typing import Callable

import RPi.GPIO as GPIO

from device.models import MoodCounts


class GpioHandler:
    def __init__(self, good_pin: int, neutral_pin: int, bad_pin: int, debounce_seconds: float = 0.25) -> None:
        self.good_pin = good_pin
        self.neutral_pin = neutral_pin
        self.bad_pin = bad_pin
        self.debounce_seconds = debounce_seconds

        self.counts = MoodCounts()
        self.last_pressed = {
            "good": 0.0,
            "neutral": 0.0,
            "bad": 0.0,
        }

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
        return MoodCounts(
            good=self.counts.good,
            neutral=self.counts.neutral,
            bad=self.counts.bad,
        )

    def _can_press(self, mood: str) -> bool:
        now = time.time()
        if now - self.last_pressed[mood] < self.debounce_seconds:
            return False
        self.last_pressed[mood] = now
        return True

    def _good_pressed(self, channel: int) -> None:
        if self._can_press("good"):
            self.counts.good += 1

    def _neutral_pressed(self, channel: int) -> None:
        if self._can_press("neutral"):
            self.counts.neutral += 1

    def _bad_pressed(self, channel: int) -> None:
        if self._can_press("bad"):
            self.counts.bad += 1
