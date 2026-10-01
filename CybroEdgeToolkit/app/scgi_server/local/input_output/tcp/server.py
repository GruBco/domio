import asyncio
import socket
from asyncio import StreamReader, StreamWriter, AbstractEventLoop
from asyncio.base_events import Server
from typing import Optional, List

from lib.general.conditional_logger import ConditionalLogger
from lib.general.tls import create_server_tls_context
from lib.startup.exceptions import TCPPortError
from scgi_server.local.input_output.scgi.scgi_server import ScgiServer
from scgi_server.local.input_output.websocket.server_handler import \
    WebSocketServerHandler


class TCPServer:
    PAYLOAD_BYTES = 16 * 1024

    def __init__(self,
                 log: ConditionalLogger,
                 loop: AbstractEventLoop,
                 handler: ScgiServer,
                 bind_address: str,
                 port: int,
                 tls_enabled: bool,
                 access_token: Optional[str]):
        self._log: ConditionalLogger = log
        self._loop: AbstractEventLoop = loop
        self._handler: ScgiServer = handler
        self._bind_address = bind_address
        self._port = port
        self._tls_enabled: bool = tls_enabled
        self._access_token: Optional[str] = access_token

        self._websockets: List[WebSocketServerHandler] = []

        self._server: Optional[Server] = None

    async def start(self):
        if self._tls_enabled:
            ssl_context = create_server_tls_context()
        else:
            ssl_context = None

        if self._bind_address == '':
            ipv6 = True
            self._bind_address = '::'
        else:
            try:
                socket.inet_pton(socket.AF_INET6, self._bind_address)
                ipv6 = True
            except socket.error:
                ipv6 = False

        sock = socket.socket(socket.AF_INET6 if ipv6 else socket.AF_INET,
                             socket.SOCK_STREAM)
        if ipv6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        try:
            sock.bind((self._bind_address, self._port))
        except OSError as e:
            raise TCPPortError(e)

        self._server = await asyncio.start_server(
            self._handle,
            sock=sock,
            start_serving=True,
            ssl=ssl_context
        )
        (host, port, *rest) = self._server.sockets[0].getsockname()
        self._log.info(lambda: f"Listening on {host}:{port}")
        #await self._server.serve_forever()
        #sock.close()

    async def send_to_clients(self, data: bytes):
        """Sends WebSocket message to all connected WebSocket clients.

        :param data: WebSocket message to send.
        """
        return await asyncio.gather(*(
            ws.send_payload(data) for ws in self._websockets
        ))

    async def _handle(self,
                      reader: StreamReader,
                      writer: StreamWriter) -> None:
        """Handler for client communication.

        :param reader: Stream reader for data sent by client.
        :param writer: Stream writer through which to send data to client.
        """
        request_bytes = await reader.read(self.PAYLOAD_BYTES)
        if request_bytes != b'':
            if request_bytes.find(b'Connection: Upgrade') != -1:
                ws = WebSocketServerHandler(
                    self._log,
                    request_bytes,
                    reader,
                    writer,
                    access_token=self._access_token
                )
                self._websockets.append(ws)
                await ws.loop()
                self._websockets.remove(ws)
            else:
                response_bytes = await self._handler.on_data(request_bytes)
                writer.write(response_bytes)
                await writer.drain()
                writer.close()
                await writer.wait_closed()
