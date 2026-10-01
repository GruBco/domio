import asyncio
import secrets
import time
from asyncio import Future, Task, AbstractEventLoop
from base64 import b64encode
from typing import Callable, Optional

from lib.general.conditional_logger import ConditionalLogger
from lib.input_output.http.messages import \
    HttpRequestMessage, HttpResponseMessage
from lib.input_output.websocket.frame import WebSocketFrame, \
    Opcode
from mqtt_client.local.input_output.tcp.client import TcpClient

DataHandlerType = Callable[[bytes], None]


class WebSocketHandshakeFailed(Exception):
    def __init__(self) -> None:
        super().__init__("WebSocket handshake failed")


class WebSocketClient:
    def __init__(self,
                 log: ConditionalLogger,
                 loop: AbstractEventLoop,
                 host: Optional[str],
                 port: int,
                 tls_enabled: bool,
                 access_token: Optional[str],
                 keepalive: float):
        self._log: ConditionalLogger = log
        self._loop: AbstractEventLoop = loop
        self._client: TcpClient = TcpClient(log, host, port, tls_enabled)
        self._access_token: Optional[str] = access_token
        self._keepalive: float = keepalive

        self._data_handler: Optional[DataHandlerType] = None
        self._hs_success = Future()
        self._ping_sent_time = time.time()

        self._pinger_task: Optional[Task] = None

        self._dead = False

    @property
    def is_dead(self) -> bool:
        """Checks if the client is running or not.

        :return: True if client is running else False
        """
        return not self._client.is_running

    async def send(self, data: bytes) -> None:
        """Sends data through websocket.

        :param data: Message to send.
        """
        frame = WebSocketFrame.for_payload(data)
        await self._client.write(frame.serialize())

    def set_data_handler(self,
                         data_handler: Optional[DataHandlerType]) -> None:
        """Registers callback for handling messages received from the
        websocket.

        :param data_handler: Callback for handling messages.
        """
        self._data_handler = data_handler

    async def _frame_response_handler(self, msg: bytes) -> None:
        """Callback for handling TCP messages.

        :param msg: Message received via TCP.
        """
        try:
            frame = WebSocketFrame.deserialize(msg)
            self._log.debug(f"frame {frame}")
            if frame.opcode == Opcode.PING:
                await self.send_pong(frame.payload)
            elif frame.opcode == Opcode.PONG:
                self._log.debug("Received pong: %s",
                                frame.payload.decode())
                if time.time() - self._ping_sent_time > self._keepalive:
                    self._client.die()
                else:
                    self._ping_sent_time = time.time()
            else:
                if self._data_handler is not None:
                    self._data_handler(frame.payload)
        except Exception as e:
            self._log.debug("Error while handling frame", exc_info=e)
            self._log.error(f"Error while handling frame {e}")

    async def _handshake_response_handler(self, msg: bytes) -> None:
        """Callback for sending responses on handshake requests.

        :param msg: Handshake request message.
        """
        response = HttpResponseMessage.parse_response(msg.decode())
        self._hs_success.set_result(response.status_code == 101)

    async def _initiate_handshake(self) -> None:
        """Initiates handshake for a websocket.
        """
        headers = {
            "Host": f"{self._client.host}:{self._client.port}",
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": b64encode(secrets.token_bytes(16)).decode(),
            "Sec-WebSocket-Version": "13"
        }
        if self._access_token is not None:
            headers['Authorization'] = f'token {self._access_token}'

        request = HttpRequestMessage(
            method="GET",
            uri="/",
            headers=headers
        )

        await self._client.write(request.serialize().encode())

    async def send_ping(self, msg: str) -> None:
        """Sends PING message through websocket.

        :param msg: Payload to send.
        """
        await self._client.write(
            WebSocketFrame.ping(msg, client=True).serialize()
        )

    async def send_pong(self, payload: bytes) -> None:
        """Sends PONG message through websocket.

        :param payload: Payload to send.
        """
        await self._client.write(
            WebSocketFrame.pong(payload, client=True).serialize()
        )

    async def start(self):
        self._log.info("Starting websocket client")
        await self._client.start()

        # before handshake set handshake response handler
        self._client.set_data_handler(self._handshake_response_handler)
        await self._initiate_handshake()

        while not self._hs_success.done():
            await asyncio.sleep(0.1)

        if not self._hs_success.result():
            await self._client.stop()
            raise WebSocketHandshakeFailed()
        else:
            # after handshake is successful set provided message handler for
            # message processing
            self._client.set_data_handler(self._frame_response_handler)

        self._ping_sent_time = time.time()
        self._pinger_task = self._loop.create_task(self._run_pinger())

        self._dead = False

    async def stop(self):
        self._log.info("Stopping websocket client")
        if self._pinger_task:
            self._pinger_task.cancel()
            await self._pinger_task

        if self._hs_success.done() and self._hs_success.result():
            await self._client.write(
                WebSocketFrame.close(1000, client=True).serialize()
            )

        await self._client.stop()
        self._hs_success = Future()

    async def _run_pinger(self):
        try:
            while self._client.is_running:
                # Because sleep takes exactly keepalive wait time, time \
                # difference will be slightly higher that keepalive time. This
                # is the reason for time delta to be subtracted by 0.1 seconds.
                if time.time() - self._ping_sent_time - 0.1 > self._keepalive:
                    self._client.die()
                await self.send_ping("!")
                self._ping_sent_time = time.time()
                await asyncio.sleep(self._keepalive)
        except asyncio.CancelledError:
            raise
