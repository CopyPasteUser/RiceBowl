"""Bounded GTK-friendly execution with stale-result suppression.

Pass `GLib.idle_add` as dispatch from a renderer. No worker is started until
submit(); callbacks execute via the renderer's supplied main-loop dispatcher.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

MAX_PENDING = 64


@dataclass(frozen=True)
class Response:
    key: str
    generation: int
    value: Any = None
    error: str | None = None


class LatestRequestRunner:
    """Use per-UI instance; close it when that window or popover is destroyed.

    Work already running cannot be interrupted safely (notably hardware
    writes). A newer request suppresses only the old UI response.
    """

    def __init__(self, dispatch: Callable[[Callable[[], bool]], Any], *, workers: int = 3):
        if not callable(dispatch) or not isinstance(workers, int) or not 1 <= workers <= 6:
            raise ValueError("A UI dispatcher and 1–6 workers are required")
        self._dispatch = dispatch
        self._executor = ThreadPoolExecutor(max_workers=workers,
                                            thread_name_prefix="riceware")
        self._lock = threading.Lock()
        self._generations: dict[str, int] = {}
        self._pending: dict[str, Future] = {}
        self._sequence = 0
        self._closed = False

    def submit(self, key: str, operation: Callable[[], Any],
               callback: Callable[[Response], None]) -> int:
        if not isinstance(key, str) or not key or len(key) > 100:
            raise ValueError("A short, stable request key is required")
        if not callable(operation) or not callable(callback):
            raise ValueError("Operation and callback must be callable")
        with self._lock:
            if self._closed:
                raise RuntimeError("Riceware request runner is closed")
            previous = self._pending.get(key)
            if previous is None and len(self._pending) >= MAX_PENDING:
                raise RuntimeError("Too many outstanding Riceware UI requests")
            if previous is not None:
                previous.cancel()  # Only queued work can be cancelled.
            self._sequence += 1
            generation = self._sequence
            self._generations[key] = generation
            future = self._executor.submit(self._execute, key, generation, operation)
            self._pending[key] = future
        # A completed Future invokes add_done_callback immediately; doing it
        # under _lock would deadlock a synchronous test/UI dispatcher.
        future.add_done_callback(
            lambda done: self._schedule(key, generation, done, callback))
        return generation

    @staticmethod
    def _execute(key: str, generation: int, operation: Callable[[], Any]) -> Response:
        try:
            return Response(key, generation, value=operation())
        except Exception as exc:
            logging.getLogger(__name__).exception("Riceware %s operation failed", key)
            return Response(key, generation, error=str(exc) or type(exc).__name__)

    def _schedule(self, key: str, generation: int, future: Future,
                  callback: Callable[[Response], None]) -> None:
        if future.cancelled():
            return
        response = future.result()

        def deliver() -> bool:
            with self._lock:
                if self._closed or self._generations.get(key) != generation:
                    return False
                self._pending.pop(key, None)
                self._generations.pop(key, None)
            try:
                callback(response)
            except Exception:
                logging.getLogger(__name__).exception("Riceware %s UI callback failed", key)
            return False

        try:
            self._dispatch(deliver)
        except Exception:
            with self._lock:
                if self._generations.get(key) == generation:
                    self._pending.pop(key, None)
                    self._generations.pop(key, None)
            logging.getLogger(__name__).exception("Riceware %s UI dispatch failed", key)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            for future in self._pending.values():
                future.cancel()
            self._pending.clear()
            self._generations.clear()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
