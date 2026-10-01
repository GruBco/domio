import asyncio
import socket
from asyncio import AbstractEventLoop, DatagramTransport
from typing import Tuple, Optional

from lib.general.conditional_logger import ConditionalLogger
from lib.startup.exceptions import UDPPortError
from scgi_server.local.input_output.abus_stack.udp.udp_activity_service \
    import UdpActivityService
from scgi_server.local.input_output.abus_stack.udp.udp_message import \
    UdpMessage
from scgi_server.local.input_output.abus_stack.udp.udp_protocol import \
    UdpProtocol


class UdpTransceiver:
    def __init__(self,
                 log: ConditionalLogger,
                 communication_loop: AbstractEventLoop,
                 transceiver: 'AbusTransceiver',
                 udp_activity_service: UdpActivityService,
                 bind_address: str,
                 port: int):
        self._log: ConditionalLogger = log
        self._communication_loop: AbstractEventLoop = communication_loop
        self._transceiver: 'AbusTransceiver' = transceiver
        self._transceiver.set_udp_sender(self)
        self._udp_activity_service: UdpActivityService = udp_activity_service
        self._bind_address: str = '0.0.0.0' if bind_address == '' else bind_address
        self._port: int = port

        self._own_bind_addr: Optional[Tuple[str, int]] = None
        self._sender: Optional[UdpProtocol] = None

    async def start(self) -> Tuple[str, int]:
        transport, _ = await asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(
                self._start(),
                self._communication_loop
            )
        )

        self._own_bind_addr: Tuple[str, int] = (
            transport.get_extra_info("socket").getsockname()[:2]
        )
        host, port = self._own_bind_addr
        self._log.info(lambda: f"Listening on {host}:{port}")

        return self._own_bind_addr

    async def _start(self) -> Tuple[DatagramTransport, UdpProtocol]:
        """communication loop
        """
        def protocol_factory() -> UdpProtocol:
            protocol = UdpProtocol(self._log, self)
            self._sender = protocol
            return protocol

        try:
            return await self._communication_loop.create_datagram_endpoint(
                protocol_factory=protocol_factory,
                local_addr=(self._bind_address, self._port),
                allow_broadcast=True,
                family=socket.AF_INET
            )
        except OSError as e:
            raise UDPPortError(e)


    def send(self, udp_msg: UdpMessage) -> None:
        """communication loop
        """
        self._udp_activity_service.report_tx()
        self._sender.send(udp_msg)

    def receive(self, udp_msg: UdpMessage) -> None:
        """communication loop
        """
        if udp_msg.addr != self._own_bind_addr:
            self._udp_activity_service.report_rx()
            self._transceiver.receive(udp_msg)
