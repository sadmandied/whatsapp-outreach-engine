"""
Outreach Campaign Background Scheduler
======================================
Enables hands-free scheduled outreach runs. Allows setting a target execution
time (e.g., 14:30) or countdown delay (e.g., in 45 minutes) with real-time UI
telemetry and thread-safe cancellation.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable


class CampaignScheduler:
    def __init__(self, on_tick: Optional[Callable[[int, str], None]] = None):
        self.on_tick = on_tick
        self._target_epoch: Optional[float] = None
        self._target_display: str = ""
        self._thread: Optional[threading.Thread] = None
        self._cancel_event = threading.Event()
        self._is_scheduled = False

    def is_active(self) -> bool:
        return self._is_scheduled and not self._cancel_event.is_set()

    def get_target_display(self) -> str:
        return self._target_display

    def cancel(self) -> None:
        """Cancels any pending schedule."""
        self._cancel_event.set()
        self._is_scheduled = False

    def schedule_in_minutes(self, minutes: int, callback: Callable[[], None]) -> None:
        """Schedules a campaign to trigger after X minutes."""
        target_dt = datetime.now() + timedelta(minutes=minutes)
        self.schedule_at(target_dt.strftime("%H:%M"), callback)

    def schedule_at(self, time_str: str, callback: Callable[[], None]) -> None:
        """
        Schedules a campaign at a specific HH:MM time today (or tomorrow if the time has passed).
        """
        self.cancel()
        self._cancel_event.clear()

        now = datetime.now()
        try:
            parts = [int(p) for p in time_str.strip().split(":")]
            target_hour = parts[0]
            target_minute = parts[1]
        except Exception as e:
            raise ValueError(f"Invalid time format '{time_str}'. Expected HH:MM.") from e

        target_dt = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if target_dt <= now:
            # If the scheduled time has already passed today, schedule for tomorrow
            target_dt += timedelta(days=1)

        self._target_epoch = target_dt.timestamp()
        self._target_display = target_dt.strftime("%I:%M %p (%b %d)")
        self._is_scheduled = True

        def worker():
            while not self._cancel_event.is_set():
                remaining = int(self._target_epoch - time.time())
                if remaining <= 0:
                    break

                hours, rem = divmod(remaining, 3600)
                mins, secs = divmod(rem, 60)
                time_repr = f"{hours:02d}:{mins:02d}:{secs:02d}"

                if self.on_tick:
                    self.on_tick(remaining, time_repr)

                time.sleep(1)

            if not self._cancel_event.is_set():
                self._is_scheduled = False
                callback()

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()
