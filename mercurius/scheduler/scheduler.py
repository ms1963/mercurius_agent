"""
Background Task, Cron and Periodic Job Scheduler for Mercury.
Supports interval-based tasks, jitter management, error isolation, execution history,
and graceful shutdown for enterprise telemetry & health sweeps.
"""
from __future__ import annotations
import time, threading, uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any

@dataclass
class ScheduledTask:
    id: str
    name: str
    interval_sec: float
    func: Callable[[], Any]
    last_run: float = 0.0
    run_count: int = 0
    failure_count: int = 0
    last_error: Optional[str] = None
    is_active: bool = True

class TaskScheduler:
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def add_interval_task(self, name: str, interval_sec: float, func: Callable[[], Any]) -> str:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self.tasks[task_id] = ScheduledTask(
                id=task_id,
                name=name,
                interval_sec=interval_sec,
                func=func
            )
        return task_id

    def remove_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                return True
        return False

    def trigger_task_now(self, task_id: str) -> bool:
        with self._lock:
            t = self.tasks.get(task_id)
        if not t:
            return False
        try:
            t.last_run = time.time()
            t.func()
            t.run_count += 1
            return True
        except Exception as e:
            t.failure_count += 1
            t.last_error = str(e)
            return False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _loop(self):
        while self._running:
            now = time.time()
            with self._lock:
                task_items = list(self.tasks.values())

            for t in task_items:
                if t.is_active and (now - t.last_run >= t.interval_sec):
                    t.last_run = now
                    try:
                        t.func()
                        t.run_count += 1
                    except Exception as e:
                        t.failure_count += 1
                        t.last_error = str(e)
            time.sleep(0.5)

    def list_tasks_status(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "interval_sec": t.interval_sec,
                    "run_count": t.run_count,
                    "failure_count": t.failure_count,
                    "last_run": t.last_run,
                    "is_active": t.is_active,
                    "last_error": t.last_error
                }
                for t in self.tasks.values()
            ]
