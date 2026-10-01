from asyncio import AbstractEventLoop
from typing import Any, Optional, Dict, Tuple

from scgi_server.local.general.async_cache import AsyncCache
from scgi_server.local.input_output.abus_stack.abus.command_frame import CommandFrame
from scgi_server.local.services.rw_service.subservices.plc_comm_service.plc_rw_request \
    import PlcRWRequest


class DataLoggerCache:
    def __init__(self, loop: AbstractEventLoop):
        self._loop: AbstractEventLoop = loop
        self._task_caches: Dict[int, AsyncCache] = dict()

    def __bool__(self) -> bool:
        return bool(self._task_caches)

    async def get(self,
                  task_id: int,
                  crc: int,
                  default: Optional[Any] = None
                  ) -> Optional[Tuple[PlcRWRequest, CommandFrame]]:
        try:
            return await self._task_caches[task_id].get(crc, default)
        except KeyError:
            return default

    def set_future(self, task_id: int, crc: int) -> None:
        task_cache = self._task_caches.get(task_id)

        if task_cache is None:
            task_cache = AsyncCache(self._loop)
            self._task_caches[task_id] = task_cache

        task_cache.set_future(crc)

    def set_future_result(
        self,
        task_id: int,
        crc: int,
        value: Optional[Tuple[PlcRWRequest, CommandFrame]]
    ) -> None:
        task_cache = self._task_caches[task_id]

        task_cache.set_future_result(crc, value)

        if not task_cache:
            del self._task_caches[task_id]

    def cancel(self, task_id: int, crc: int) -> None:
        task_cache = self._task_caches[task_id]

        task_cache.cancel(crc)

        if not task_cache:
            del self._task_caches[task_id]

    def clear(self) -> None:
        keys_to_delete = []

        for key in self._task_caches:
            self._task_caches[key].clear()
            keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._task_caches[key]
