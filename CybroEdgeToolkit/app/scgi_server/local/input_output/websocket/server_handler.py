import asyncio
from asyncio import StreamReader, StreamWriter
from base64 import b64encode
from hashlib import sha1
from typing import Optional

from lib.general.conditional_logger import ConditionalLogger
from lib.input_output.http.messages import \
    HttpRequestMessage, HttpResponseMessage
from lib.input_output.websocket.frame import Opcode, \
    WebSocketFrame


class WebSocketServerHandler:
    magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self,
                 log: ConditionalLogger,
                 handshake_request: bytes,
                 reader: StreamReader,
                 writer: StreamWriter,
                 access_token: Optional[str] = None):
        self._log: ConditionalLogger = log
        self._reader: StreamReader = reader
        self._writer: StreamWriter = writer
        self._access_token: Optional[str] = access_token

        request = HttpRequestMessage.parse_request(handshake_request.decode())
        self._web_socket_key: str = request.headers['Sec-WebSocket-Key']

        auth_hdr = request.headers.get('Authorization')
        self._request_access_token: Optional[str] = (
            None if auth_hdr is None else auth_hdr.split(' ')[1]
        )

    async def _send(self, data: bytes) -> None:
        self._writer.write(data)
        await self._writer.drain()

    def _accept_value(self) -> bytes:
        """Create Sec-WebSocket-Accept value from received Sec-WebSocket-Key
        value.
        """
        return b64encode(sha1(
            (self._web_socket_key + self.magic).encode()
        ).digest())

    def _handshake_response(self) -> str:
        """Create http handshake response for websocket initialization.
        """
        return str(HttpResponseMessage(
            status_code=101,
            status_message="Switching Protocols",
            headers={
                'Upgrade': 'websocket',
                'Connection': 'Upgrade',
                'Sec-WebSocket-Accept': self._accept_value().decode(),
            }
        ))

    async def send_handshake_response(self):
        await self._send(self._handshake_response().encode())

    async def send_frame(self, frame: WebSocketFrame) -> None:
        """Serializes and send frame.
        """
        self._log.debug(f"WS send {frame}")
        await self._send(frame.serialize())

    async def send_payload(self, data: bytes) -> None:
        """Create WS frame for data and sends serialized frame.
        """
        await self.send_frame(WebSocketFrame.for_payload(data))

    async def loop(self):
        if (
            self._access_token is not None and
            self._request_access_token != self._access_token
        ):
            self._log.error("Unauthorized: Access token mismatch")
            await self._send(
                HttpResponseMessage.unauthorized().serialize().encode()
            )
        else:
            await self.send_handshake_response()

            while True:
                msg = await self._reader.read(8120)
                if len(msg) == 0:
                    self._log.warning("received zero data, closing connection")
                    break

                frame = WebSocketFrame.deserialize(msg)
                self._log.debug(f"WS recv {frame}")

                # client side messages must use mask
                if not frame.has_mask:
                    self._log.warning("Non-masked client message, "
                                      "closing connection")
                    break

                # close connection on client request
                if frame.opcode == Opcode.CLOSE:
                    self._log.info("Closing websocket connection")
                    break

                # respond to ping
                if frame.opcode == Opcode.PING:
                    pong_frame = WebSocketFrame.pong(frame.payload)
                    await self.send_frame(pong_frame)

                await asyncio.sleep(1)

        self._writer.close()
        await self._writer.wait_closed()
