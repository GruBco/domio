from typing import Optional, Tuple

from lib.general.conditional_logger import ConditionalLogger
from scgi_server.local.defaults import AUTODETECT_NAD, ABUS_BROADCAST_PORT
from scgi_server.local.errors import ScgiServerError
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


class PlcDetectionService:
    def __init__(self,
                 log: ConditionalLogger,
                 plc_info_service: 'PlcInfoService',
                 eth_autodetect_enabled: bool,
                 eth_autodetect_address: str,
                 trans_id_generator: TransactionIdGeneratorType):
        self._log: ConditionalLogger = log
        self._plc_info_service: 'PlcInfoService' = plc_info_service
        self._eth_autodetect_enabled: bool = eth_autodetect_enabled
        self._eth_autodetect_address: str = eth_autodetect_address

        self._nad: int = AUTODETECT_NAD
        self._transaction_id_generator = trans_id_generator
        self._exchanger: Optional[AbusExchanger] = None

    def set_exchanger(self, exchanger: AbusExchanger):
        self._exchanger = exchanger

    async def detect(self, nad: int) -> Optional[str]:
        try:
            self._log.info(lambda: f"Detecting ip for c{nad}")
            ip = await self._ping_and_get_ip(nad)
            self._log.info(lambda: f"Detected ip {ip} for c{nad}")
            return ip
        except ExchangerTimeoutError as e:
            self._log.warning(lambda: f"Couldn't detect ip for c{nad}")
            raise e

    async def _ping_and_get_ip(self, nad: int) -> Optional[str]:
        plc_info = self._plc_info_service.get_plc_info(nad)

        error = None

        if self._eth_autodetect_enabled:
            ping_msg = self._create_broadcast_ping_message(plc_info)
            try:
                return await self._detect_with_ping_message(ping_msg)
            except ExchangerTimeoutError as e:
                error = e

        if error is None:
            error = ScgiServerError(
                'Autodetect failed because response not received'
            )

        raise error

    async def _detect_with_ping_message(self, ping_msg: AbusMessage) -> str:
        response = await self._exchanger.exchange_threadsafe(ping_msg)
        ip, _ = response.addr

        return ip

    def _create_zero_ping_message(self, plc_info: PlcInfo) -> AbusMessage:
        address = ('0.0.0.0', 0)
        return self._create_ping_message_with_address(plc_info, address)

    def _create_broadcast_ping_message(self, plc_info: PlcInfo) -> AbusMessage:
        address = (self._eth_autodetect_address, ABUS_BROADCAST_PORT)
        return self._create_ping_message_with_address(plc_info, address)

    def _create_ping_message_with_address(self,
                                          plc_info: PlcInfo,
                                          address: Tuple[str, int]
                                          ) -> AbusMessage:
        return AbusMessage(
            address,
            self._nad,
            plc_info.nad,
            self._get_transaction_id(plc_info),
            CommandFrameUtil.create_ping()
        )

    def _get_transaction_id(self, plc_info):
        password = plc_info.password
        return next(self._transaction_id_generator) \
            if password is None \
            else password
