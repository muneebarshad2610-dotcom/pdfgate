import asyncio
import logging

log = logging.getLogger("house_of_games.timer")


class RoundTimer:

    def __init__(self):
        self._tasks = {}
        self._remaining = {}

    def start(self, timer_id: str, duration: int, callback=None):
        self.cancel(timer_id)
        self._remaining[timer_id] = duration

        async def _run():
            try:
                for remaining in range(duration, 0, -1):
                    self._remaining[timer_id] = remaining
                    await asyncio.sleep(1)
                self._remaining[timer_id] = 0
                if callback:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
            except asyncio.CancelledError:
                pass
            finally:
                self._tasks.pop(timer_id, None)
                self._remaining.pop(timer_id, None)

        self._tasks[timer_id] = asyncio.create_task(_run())
        log.debug("Timer started: %s (%ds)", timer_id, duration)

    def cancel(self, timer_id: str):
        task = self._tasks.pop(timer_id, None)
        if task is not None:
            task.cancel()
            self._remaining.pop(timer_id, None)
            log.debug("Timer cancelled: %s", timer_id)

    def get_remaining(self, timer_id: str):
        return self._remaining.get(timer_id, 0)

    def cancel_all(self):
        for timer_id in list(self._tasks.keys()):
            self.cancel(timer_id)

    @property
    def active_timers(self):
        return list(self._tasks.keys())
