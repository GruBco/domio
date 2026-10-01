import asyncio
from asyncio import StreamWriter, StreamReader, AbstractEventLoop, Task, \
    CancelledError
from typing import Callable, Awaitable, Optional

from lib.general.conditional_logger import ConditionalLogger
from lib.general.tls import create_client_tls_context


class TcpClient:
    def __init__(self,
                 log: ConditionalLogger,
                 host: Optional[str],
                 port: int,
                 tls_enabled: bool,
                 read_buffer_size: int = 4096):
        self._log: ConditionalLogger = log
        self._host: Optional[str] = host
        self._port: int = port
        self._tls_enabled: bool = tls_enabled
        self._read_buffer_size: int = read_buffer_size

        self._writer: Optional[StreamWriter] = None
        self._reader: Optional[StreamReader] = None
        self._data_handler: Optional[Callable[[bytes], Awaitable[None]]] = None
        self._running = False
        self._read_task: Optional[Task] = None

        self._loop: Optional[AbstractEventLoop] = None

    @property
    def host(self) -> Optional[str]:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def is_running(self) -> bool:
        return self._running

    def set_data_handler(self,
                         handler: Optional[Callable[[bytes], Awaitable[None]]]
                         ) -> None:
        self._data_handler = handler

    async def _reader_task(self):
        try:
            while self.is_running:
                if self._reader is None:
                    break

                try:
                    msg = await self._reader.read(self._read_buffer_size)
                    if len(msg) == 0:
                        self._running = False
                    else:
                        self._log.debug("read %s", msg)
                        if self._data_handler is not None:
                            await self._data_handler(msg)
                except TimeoutError:
                    pass
        except CancelledError:
            raise

    async def write(self, data: bytes):
        self._log.debug("write %s", data)
        if self._writer is None:
            self._log.error("Not connected")
        else:
            self._writer.write(data)
            await self._writer.drain()

    async def stop(self):
        self._log.info("Stopping tcp client")
        self._running = False

        if self._read_task:
            self._read_task.cancel()
            await self._read_task
            self._read_task = None

        if self._reader:
            self._reader = None

        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None

    async def start(self):
        self._log.info(f"Starting tcp client: {self._host}:{self._port}")
        reader, writer = await asyncio.open_connection(
            self._host, self._port
        )
        if self._tls_enabled:
            await writer.start_tls(create_client_tls_context())

        self._writer = writer
        self._reader = reader
        self._read_task = asyncio.create_task(self._reader_task())

        self._running = True

    def die(self):
        self._running = False
