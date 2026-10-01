import asyncio
from asyncio import AbstractEventLoop
from datetime import timedelta
from typing import Dict

from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .plc_cache.single_plc_cache import SinglePlcCache


class PlcCache:
    def __init__(self,
                 loop: AbstractEventLoop,
                 cleanup_period: timedelta,
                 request_period: timedelta,
                 valid_period: timedelta):
        self._loop: AbstractEventLoop = loop
        self._plc_caches: Dict[int, SinglePlcCache] = {}
        self._request_period: timedelta = request_period
        self._valid_period: timedelta = valid_period

        cleanup_period_s = cleanup_period.total_seconds()

        if cleanup_period_s != 0:
            self._task = self._loop.create_task(
                self._cleanup_task(cleanup_period_s)
            )
        else:
            self._task = None

    def __getitem__(self, nad: int) -> SinglePlcCache:
        try:
            return self._plc_caches[nad]
        except KeyError:
            result = SinglePlcCache(
                self._loop,
                self._request_period,
                self._valid_period
            )
            self._plc_caches[nad] = result
            return result

    async def _cleanup_task(self, cleanup_period: float) -> None:
        while True:
            await asyncio.sleep(cleanup_period)
            self._cleanup()

    def _cleanup(self) -> None:
        for nad in self._plc_caches:
            self._plc_caches[nad].cleanup()
