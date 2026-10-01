from asyncio import AbstractEventLoop
from datetime import timedelta
from typing import Optional, Dict

from lib.general.conditional_logger import ConditionalLogger
from scgi_server.local.defaults import PUSH_NAD, RW_NAD, AUTODETECT_NAD
from scgi_server.local.input_output.abus_stack.abus.abus_exchanger import \
    AbusExchanger
from scgi_server.local.input_output.abus_stack.abus.abus_message import \
    AbusMessage
from scgi_server.local.services.plc_detection_service.plc_detection_service \
    import PlcDetectionService
from scgi_server.local.services.push_service.push_service import PushService
from scgi_server.local.services.rw_service.rw_service import RWService
from scgi_server.local.services.socket_service.socket_service import \
    SocketService


class Router:
    """Routes received abus messages by destination nad to designated
    receivers.
    """

    def __init__(self,
                 log: ConditionalLogger,
                 communication_loop: AbstractEventLoop,
                 push_service: PushService,
                 detection_service: PlcDetectionService,
                 rw_service: RWService,
                 socket_service: SocketService,
                 push_enabled: bool,
                 abus_timeout_ms: timedelta,
                 abus_number_of_retries: int):
        self._log: ConditionalLogger = log
        self._sender: Optional['AbusTransceiver'] = None
        self._receivers_by_nad: Dict[int, AbusExchanger] = {}
        self._push_receiver: PushService = push_service
        self._socket_service: SocketService = socket_service

        if push_enabled:
            push_exchanger = AbusExchanger(
                communication_loop,
                self,
                abus_timeout_ms,
                abus_number_of_retries
            )
            self._receivers_by_nad[PUSH_NAD] = push_exchanger
            push_service.set_exchanger(push_exchanger)
            self._push_receiver = push_service

        detection_exchanger = AbusExchanger(
            communication_loop,
            self,
            abus_timeout_ms,
            abus_number_of_retries
        )
        self._receivers_by_nad[AUTODETECT_NAD] = detection_exchanger
        detection_service.set_exchanger(detection_exchanger)

        rw_exchanger = AbusExchanger(
            communication_loop,
            self,
            abus_timeout_ms,
            abus_number_of_retries
        )
        self._receivers_by_nad[RW_NAD] = rw_exchanger
        rw_service.set_exchanger(rw_exchanger)
        self._receivers_by_nad[0] = rw_exchanger

    def set_sender(self, sender: 'AbusTransceiver'):
        self._sender = sender

    def send(self, abus_msg: AbusMessage) -> None:
        """communication loop"""
        self._sender.send(abus_msg)

    def receive(self, abus_msg: AbusMessage) -> None:
        """communication loop"""
        is_push = abus_msg.is_push
        is_socket = abus_msg.is_socket

        if is_push:
            self._push_receiver.receive(abus_msg)
        elif is_socket:
            self._socket_service.receive(abus_msg)
        elif abus_msg.to_nad != 0:
            if abus_msg.to_nad in self._receivers_by_nad:
                self._receivers_by_nad[abus_msg.to_nad].receive(abus_msg)
            else:
                self._log.debug(f"No receiver for nad {abus_msg.to_nad}")
        else:
            self._log.debug(f"Received non push or socket message for nad 0: "
                            f"{abus_msg}")
