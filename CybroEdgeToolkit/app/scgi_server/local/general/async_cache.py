import asyncio
from asyncio import AbstractEventLoop, Future
from typing import Any, Optional, Tuple, Dict

from scgi_server.local.input_output.abus_stack.abus.command_frame import CommandFrame
from scgi_server.local.services.rw_service.subservices.plc_comm_service.plc_rw_request \
    import PlcRWRequest


class AsyncCache:
    def __init__(self, loop: AbstractEventLoop):
        self._loop: AbstractEventLoop = loop
        self._futures: Dict[int, Future] = {}

    def __bool__(self) -> bool:
        return bool(self._futures)

    async def get(self,
                  key: int,
                  default: Optional[Any] = None
                  ) -> Tuple[PlcRWRequest, CommandFrame]:
        try:
            res = await self._futures[key]

            return res
        except (KeyError, asyncio.CancelledError):
            return default

    def set_future(self, key: int) -> None:
        self._futures[key] = self._loop.create_future()

    def set_future_result(
        self,
        key: int,
        value: Optional[Tuple[PlcRWRequest, CommandFrame]]
    ) -> None:
        self._futures[key].set_result(value)

    def cancel(self, key: int) -> None:
        self._futures[key].cancel()
        del self._futures[key]

    def clear(self) -> None:
        for key in self._futures:
            self.cancel(key)
