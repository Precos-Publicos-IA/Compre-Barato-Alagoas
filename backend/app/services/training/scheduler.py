"""In-process daily scheduler for the catalog training job.

Runs :class:`DailyTrainingJob` on an interval. Because a production deploy runs
several worker processes, each worker would otherwise fire the job — so before
running we grab a Redis day-lock (``SET NX EX``); only the worker that wins it
executes. The lock TTL covers the interval so a crashed run re-runs next tick.

Disabled by default (``training_scheduler_enabled``); ``run_training_once`` is
also exposed for the admin manual-trigger endpoint (which skips the day-lock).
"""

from __future__ import annotations

import asyncio
import logging
import time

from ..catalog.manager import CatalogManager
from .daily_job import DailyTrainingJob, TrainingResult
from .flags import TrainingFlagStore

logger = logging.getLogger(__name__)


async def run_training_once(app, *, use_lock: bool = False) -> TrainingResult | None:
    """Run one training cycle using clients from ``app.state``.

    When ``use_lock`` is set, only the worker that acquires the Redis day-lock
    runs; the rest return ``None``. Manual admin triggers pass ``use_lock=False``.
    """
    state = app.state
    catalog: CatalogManager = state.catalog
    flag_store: TrainingFlagStore = state.flag_store

    if use_lock:
        day = time.strftime("%Y-%m-%d", time.gmtime())
        key = f"training:daylock:{day}"
        ttl = max(3600, int(getattr(state.settings, "training_interval_hours", 24)) * 3600)
        try:
            got = await state.cache.redis.set(key, "1", nx=True, ex=ttl)
        except Exception:
            logger.exception("training day-lock check failed; skipping this tick")
            return None
        if not got:
            logger.debug("training day-lock held by another worker; skipping")
            return None

    job = DailyTrainingJob(
        catalog=catalog,
        flag_store=flag_store,
        llm_client=getattr(state, "validation_llm", None),
        sefaz_client=getattr(state, "sefaz", None),
    )
    result = await job.run()
    logger.info(
        "training run done: %d flags, %d products updated, %d new, %d queries tested",
        result.processed_flags, result.products_updated,
        result.new_products_added, result.queries_tested,
    )
    return result


class TrainingScheduler:
    """Owns the background training task and its lifecycle."""

    def __init__(self, app):
        self._app = app
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    def start(self) -> None:
        settings = self._app.state.settings
        if not getattr(settings, "training_scheduler_enabled", False):
            logger.info("training scheduler disabled")
            return
        self._task = asyncio.create_task(self._loop())
        logger.info("training scheduler started (every %sh)",
                    getattr(settings, "training_interval_hours", 24))

    async def _loop(self) -> None:
        interval = max(1, int(getattr(self._app.state.settings, "training_interval_hours", 24))) * 3600
        while not self._stopped.is_set():
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=interval)
                return  # stop() fired
            except asyncio.TimeoutError:
                pass  # interval elapsed -> run
            try:
                await run_training_once(self._app, use_lock=True)
            except Exception:
                logger.exception("scheduled training run failed")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=10)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()


def start_training_scheduler(app) -> TrainingScheduler:
    sched = TrainingScheduler(app)
    sched.start()
    return sched
