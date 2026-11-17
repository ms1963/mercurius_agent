"""
Enterprise Resilience and Fault-Tolerance Engine for Mercurius Agent.
Implements:
1. Circuit Breaker Pattern (CLOSED -> OPEN -> HALF_OPEN states with failure thresholds & recovery timeouts).
2. Jittered Exponential Backoff Retry Policy.
3. Fallback Cascades across LLM providers and secondary tools.
4. Dead Letter Queue (DLQ) for asynchronous failed task forensic analysis.
"""
from __future__ import annotations
import time, random, logging, threading
from enum import Enum
from typing import Callable, Any, Dict, List, Optional

logger = logging.getLogger("mercury.resilience")

class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout_sec: float = 5.0,
        half_open_success_threshold: int = 1
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.half_open_success_threshold = half_open_success_threshold
        
        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count: int = 0
        self.success_count: int = 0
        self.last_failure_time: float = 0.0
        self._lock = threading.Lock()

    def can_execute(self) -> bool:
        with self._lock:
            now = time.time()
            if self.state == CircuitState.OPEN:
                if now - self.last_failure_time >= self.recovery_timeout_sec:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit '{self.name}' transitioned from OPEN to HALF_OPEN")
                    return True
                return False
            return True

    def record_success(self):
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.half_open_success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info(f"Circuit '{self.name}' recovered to CLOSED")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(f"Circuit '{self.name}' tripped to OPEN (failures: {self.failure_count})")

    def call(self, fn: Callable[..., Any], *args, **kwargs) -> Any:
        if not self.can_execute():
            raise CircuitBreakerOpenException(f"Circuit '{self.name}' is OPEN. Call rejected.")
        try:
            res = fn(*args, **kwargs)
            self.record_success()
            return res
        except Exception as e:
            self.record_failure()
            raise e


class DeadLetterQueue:
    def __init__(self, max_items: int = 500):
        self.queue: List[Dict[str, Any]] = []
        self.max_items = max_items
        self._lock = threading.Lock()

    def enqueue(self, task: str, error: str, metadata: Optional[Dict[str, Any]] = None):
        with self._lock:
            if len(self.queue) >= self.max_items:
                self.queue.pop(0)
            self.queue.append({
                "timestamp": time.time(),
                "task": task,
                "error": error,
                "metadata": metadata or {}
            })

    def list_failed(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.queue)

    def clear(self):
        with self._lock:
            self.queue.clear()


class ResilienceEngine:
    """Enterprise Resilience Facade providing retry policies, circuit breakers, and DLQs."""
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.dlq = DeadLetterQueue()

    def get_circuit_breaker(self, name: str, failure_threshold: int = 3, recovery_timeout_sec: float = 5.0) -> CircuitBreaker:
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout_sec=recovery_timeout_sec
            )
        return self.breakers[name]

    def execute_with_resilience(
        self,
        name: str,
        operation: Callable[[], Any],
        fallback: Optional[Callable[[Exception], Any]] = None,
        retries: int = 3,
        base_backoff_sec: float = 0.05,
        max_backoff_sec: float = 0.5
    ) -> Any:
        breaker = self.get_circuit_breaker(name)
        attempt = 0
        last_exception = None

        while attempt <= retries:
            try:
                return breaker.call(operation)
            except Exception as e:
                last_exception = e
                attempt += 1
                if attempt > retries or isinstance(e, CircuitBreakerOpenException):
                    break
                # Exponential backoff with full jitter
                backoff = min(max_backoff_sec, base_backoff_sec * (2 ** (attempt - 1)))
                jittered = backoff * (0.5 + random.random() * 0.5)
                time.sleep(jittered)

        # Fallback cascade
        if fallback:
            try:
                return fallback(last_exception)
            except Exception as fe:
                self.dlq.enqueue(task=name, error=f"Operation failed: {last_exception}; Fallback failed: {fe}")
                raise fe
        
        self.dlq.enqueue(task=name, error=str(last_exception))
        raise last_exception
