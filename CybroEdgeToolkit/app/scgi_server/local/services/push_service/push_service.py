import asyncio
from asyncio import AbstractEventLoop
from typing import Optional

from lib.general.conditional_logger import ConditionalLogger
from scgi_server.local.defaults import MAX_FRAME_BYTES, PUSH_NAD
from scgi_server.local.general.errors import ExchangerTimeoutError
from scgi_server.local.general.transaction_id_generator import \
    TransactionIdGeneratorType
from scgi_server.local.input_output.abus_stack.abus.abus_exchanger import \
    AbusExchanger
from scgi_server.local.input_output.abus_stack.abus.abus_message import \
    AbusMessage
from scgi_server.local.input_output.abus_stack.abus.command_frame import \
    CommandFrameUtil
from scgi_server.local.services.plc_info_service.plc_info import PlcInfo
from scgi_server.local.services.plc_info_service.plc_info_service import \
    PlcInfoService
from scgi_server.local.services.push_service.push_activity_service import \
    PushActivityService
from scgi_server.local.services.rw_service.subservices.plc_activity_service \
    .plc_activity_service import PlcActivityService


class PushService:
    def __init__(self,
                 log: ConditionalLogger,
                 loop: AbstractEventLoop,
                 plc_info_service: PlcInfoService,
                 plc_activity_service: PlcActivityService,
                 push_activity_service: PushActivityService,
                 trans_id_generator: TransactionIdGeneratorType):
        self._log: ConditionalLogger = log
        self._loop: AbstractEventLoop = loop
        self._plc_info_service: PlcInfoService = plc_info_service
        self._plc_activity_service: PlcActivityService = plc_activity_service
        self._push_activity_service: PushActivityService = (
            push_activity_service
        )
        self._nad: int = PUSH_NAD
        self._max_frame_length: int = MAX_FRAME_BYTES
        self._transaction_id_generator = trans_id_generator
        self._exchanger: Optional[AbusExchanger] = None

    def set_exchanger(self, exchanger: AbusExchanger) -> None:
        self._exchanger = exchanger

    def receive(self, abus_msg: AbusMessage) -> None:
        """communication loop"""
        if abus_msg.is_push:
            asyncio.run_coroutine_threadsafe(self._handle_push(abus_msg),
                                             self._loop)

    async def _handle_push(self, abus_msg: AbusMessage) -> None:
        self._push_activity_service.report_push_request_received()
        self._log.debug(lambda: f"Push from c{abus_msg.from_nad} received")

        plc_nad = abus_msg.from_nad
        (ip, port) = abus_msg.addr
        push_ack_message = self._create_push_ack_message(ip, port, plc_nad)

        try:
            await self._exchanger.exchange_threadsafe(push_ack_message)
            self._push_activity_service.report_push_acknowledgment_succeeded()
            self._plc_info_service.update(
                plc_nad,
                ip,
                port,
                PlcInfo.Origin.PUSH
            )
            self._log.debug(lambda: f"Push from c{plc_nad} acknowledged")
        except ExchangerTimeoutError as e:
            self._push_activity_service.report_push_acknowledgment_failed()
            self._log.debug(lambda: f"Push from c{plc_nad} acknowledgment "
                                    f"failed with timeout",
                            exc_info=e)

    def _create_push_ack_message(self,
                                 ip: str,
                                 port: int,
                                 nad: int) -> AbusMessage:
        addr = (ip, port)
        transaction_id = next(self._transaction_id_generator)
        command_frame = CommandFrameUtil.create_push_ack()

        return AbusMessage(addr, self._nad, nad, transaction_id, command_frame)
