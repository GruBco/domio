from asyncio import DatagramProtocol
from typing import Optional, Tuple

from lib.general.conditional_logger import ConditionalLogger
from scgi_server.local.input_output.abus_stack.udp.udp_message import \
    UdpMessage


class UdpProtocol(DatagramProtocol):
    def __init__(self, log: ConditionalLogger, receiver: 'UdpTransceiver'):
        self._log: ConditionalLogger = log
        self._receiver: 'UdpTransceiver' = receiver
        self._transport = None

    def send(self, udp_msg: UdpMessage):
        self._log.debug(f'OUT {udp_msg.addr} {udp_msg.data.hex()}')
        self._transport.sendto(udp_msg.data, udp_msg.addr)

    def receive(self, udp_msg: UdpMessage):
        self._log.debug(f'IN {udp_msg.addr} {udp_msg.data.hex()}')
        self._receiver.receive(udp_msg)

    def connection_made(self, transport):
        self._log.debug(f"Connection established")
        self._transport = transport

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self._log.debug(f"Connection lost", exc_info=exc)
        self._log.error(f"Connection lost: {exc}")
        self._transport = None

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        udp_msg = UdpMessage(data, addr)
        self.receive(udp_msg)

    def error_received(self, exc: Exception) -> None:
        self._log.debug(f"Error received", exc_info=exc)
        self._log.error(f"Error received: {exc}")
