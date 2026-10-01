from typing import Optional

from lib.general.conditional_logger import ConditionalLogger
from scgi_server.local.input_output.abus_stack.abus.abus_message import \
    AbusMessageUtil, AbusMessage
from scgi_server.local.input_output.abus_stack.abus.errors import AbusError
from scgi_server.local.input_output.abus_stack.router import Router
from scgi_server.local.input_output.abus_stack.udp.udp_message import \
    UdpMessage
from scgi_server.local.input_output.abus_stack.udp.udp_transceiver import \
    UdpTransceiver


class AbusTransceiver:
    def __init__(self,
                 log: ConditionalLogger,
                 receiver: Router):
        self._log: ConditionalLogger = log
        self._receiver: Router = receiver
        self._receiver.set_sender(self)

        self._udp_sender: Optional[UdpTransceiver] = None

    def set_udp_sender(self, sender: UdpTransceiver) -> None:
        self._udp_sender = sender

    def send(self, abus_msg: AbusMessage) -> None:
        """Communication loop.
        """
        self._send_via_udp(abus_msg)

    def receive(self, msg: UdpMessage) -> None:
        """Communication loop.
        """
        self._receive_udp_msg(msg)

    def _send_via_udp(self, abus_msg: AbusMessage) -> None:
        """Communication loop.
        """
        self._log.debug(lambda: f"Send UDP: {abus_msg}")
        udp_msg = self._abus_msg_to_udp_msg(abus_msg)
        self._udp_sender.send(udp_msg)

    def _receive_udp_msg(self, udp_msg: UdpMessage) -> None:
        """Communication loop.
        """
        abus_msg = self._udp_msg_to_abus_msg(udp_msg)
        if abus_msg is not None:
            self._log.debug(lambda: f"Receive UDP: {abus_msg}")
            self._receiver.receive(abus_msg)

    @classmethod
    def _abus_msg_to_udp_msg(cls, abus_msg: AbusMessage) -> UdpMessage:
        """communication loop"""
        return AbusMessageUtil.abus_msg_to_udp_msg(abus_msg)

    def _udp_msg_to_abus_msg(self, udp_msg: UdpMessage) -> AbusMessage:
        """communication loop"""
        try:
            return AbusMessageUtil.udp_msg_to_abus_msg(udp_msg)
        except AbusError as e:
            self._log.debug(f"Received invalid data\n{udp_msg}",
                            exc_info=e)
            self._log.error(f"Received invalid data: {e}\n{udp_msg}")
