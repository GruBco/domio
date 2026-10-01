import asyncio
from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop
from datetime import datetime, timedelta

from scgi_server.local.defaults import PLC_INFO_CLEAR_PERIOD, PLC_INFO_LIFETIME
from lib.general.conditional_logger import ConditionalLogger
from scgi_server.local.services.plc_info_service.plc_info import PlcInfo
from scgi_server.local.services.plc_info_service.plc_info_service import \
    PlcInfoService


class Timer(ABC):
    def __init__(self, loop: AbstractEventLoop, duration_s: float):
        self._loop: AbstractEventLoop = loop
        self._duration_s: float = duration_s

    async def start(self):
        await self._loop.create_task(self._execute_wait_and_repeat())

    async def _execute_wait_and_repeat(self):
        while True:
            start_time = datetime.now()
            await self.execute()
            end_time = datetime.now()
            duration = end_time - start_time
            delay = self._duration_s - duration.total_seconds()
            await asyncio.sleep(delay)

    @abstractmethod
    async def execute(self):
        pass


class PlcInfoCleaner(Timer):
    """Periodically cleans list of PLCs. PLCs which didn't respond in specified
    period are removed from the list.
    """
    def __init__(self,
                 log: ConditionalLogger,
                 loop: AbstractEventLoop,
                 plc_info_service: PlcInfoService):
        super().__init__(
            loop,
            timedelta(minutes=PLC_INFO_CLEAR_PERIOD).total_seconds()
        )

        self._log: ConditionalLogger = log
        self._plc_info_service: PlcInfoService = plc_info_service
        self._plc_info_lifetime = timedelta(minutes=PLC_INFO_LIFETIME)

    async def execute(self) -> None:
        nads_to_remove = [
            plc_info.nad for plc_info in self._plc_info_service.get_plc_infos()
            if self._should_remove_plc_info(plc_info)
        ]

        for nad in nads_to_remove:
            await self._plc_info_service.remove_plc_info(nad)

    def _should_remove_plc_info(self, plc_info: PlcInfo) -> bool:
        if (
            plc_info.origin == plc_info.Origin.PROXY or
            plc_info.origin == plc_info.Origin.STATIC
        ):
            return False

        plc_info_age = datetime.now() - plc_info.last_update_time

        return plc_info_age > self._plc_info_lifetime
