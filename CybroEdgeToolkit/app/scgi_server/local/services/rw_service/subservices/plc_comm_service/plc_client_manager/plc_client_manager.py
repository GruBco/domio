from asyncio import CancelledError, AbstractEventLoop, Future
from typing import Optional, Dict

from lib.general.conditional_logger import ConditionalLogger
from lib.general.misc import create_task_callback
from lib.services.cpu_intensive_task_runner import \
    CPUIntensiveTaskRunner
from scgi_server.local.defaults import MAX_FRAME_BYTES, RW_NAD
from scgi_server.local.errors import ScgiServerError
from scgi_server.local.general.errors import ExchangerTimeoutError
from scgi_server.local.general.transaction_id_generator import \
    TransactionIdGeneratorType
from scgi_server.local.input_output.abus_stack.abus.abus_exchanger import \
    AbusExchanger
from scgi_server.local.services.plc_detection_service.plc_detection_service \
    import PlcDetectionService
from scgi_server.local.services.plc_info_service.plc_info import PlcInfo
from scgi_server.local.services.rw_service.subservices.plc_activity_service \
    .plc_activity_service import PlcActivityService
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .plc_client_manager.plc_client.plc_client import PlcClient


class PlcClientManager:
    def __init__(
        self,
        log: ConditionalLogger,
        client_log: ConditionalLogger,
        loop: AbstractEventLoop,
        plc_info_service: 'PlcInfoService',
        plc_activity_service: PlcActivityService,
        detection_service: PlcDetectionService,
        cpu_intensive_task_runner: CPUIntensiveTaskRunner,
        trans_id_generator: TransactionIdGeneratorType
    ):
        self._log: ConditionalLogger = log
        self._client_log: ConditionalLogger = client_log
        self._loop: AbstractEventLoop = loop
        self._nad: int = RW_NAD
        self._plc_info_service: 'PlcInfoService' = plc_info_service
        self._plc_activity_service: PlcActivityService = plc_activity_service
        self._max_frame_length: int = MAX_FRAME_BYTES
        self._plc_detection_service: PlcDetectionService = detection_service
        self._plc_clients_by_nad: Dict[int, Future] = {}
        self._cpu_intensive_task_runner: CPUIntensiveTaskRunner = (
            cpu_intensive_task_runner
        )
        self._transaction_id_generator = trans_id_generator

        self._exchanger: Optional[AbusExchanger] = None

    def set_exchanger(self, exchanger: AbusExchanger) -> None:
        self._exchanger = exchanger

    def on_plc_info_set(self, plc_info: PlcInfo) -> None:
        if plc_info.origin == PlcInfo.Origin.PROXY:
            return

        nad = plc_info.nad

        if plc_info.has_ip:
            self._set(nad, self._create_plc_client(plc_info))
        elif plc_info.origin == PlcInfo.Origin.STATIC:
            self._set(nad, None)
        else:
            self._remove(nad)
            future_plc_client = self._loop.create_future()
            self._plc_clients_by_nad[nad] = future_plc_client

            if self._plc_detection_service is not None:
                self._log.info(f"Set pending plc client c{plc_info.nad}")
                self._loop \
                    .create_task(self._autodetect(plc_info)) \
                    .add_done_callback(create_task_callback(self._log))
            else:
                future_plc_client.cancel()

    def on_plc_info_removed(self, nad: int) -> None:
        self._remove(nad)

    async def get(self, nad: int) -> Optional[PlcClient]:
        try:
            try:
                return await self._plc_clients_by_nad[nad]
            except KeyError:
                plc_info = self._plc_info_service.create(
                    PlcInfo.Origin.AUTO, nad
                )
                self._plc_info_service.set_plc_info(plc_info)
                return await self._plc_clients_by_nad[nad]
        except CancelledError:
            return None

    def _set(self, nad: int, plc_client: Optional[PlcClient]) -> None:
        try:
            future_plc_client = self._plc_clients_by_nad[nad]
            if not future_plc_client.done():
                future_plc_client.set_result(plc_client)
            else:
                self._create_future_and_set_immediately(nad, plc_client)
        except KeyError:
            self._create_future_and_set_immediately(nad, plc_client)

        def log_msg() -> str:
            result = f"Added plc client c{nad}"
            if plc_client is not None:
                result += f": {plc_client.plc_info}"
            return result

        self._log.info(log_msg)

    def _remove(self, nad: int) -> None:
        try:
            future_plc_client = self._plc_clients_by_nad[nad]
            future_plc_client.cancel()
        except KeyError:
            pass

        try:
            del self._plc_clients_by_nad[nad]
        except KeyError:
            pass

        self._log.info(f"Removed plc client c{nad}")

    def _create_future_and_set_immediately(self,
                                           nad: int,
                                           plc_client: PlcClient) -> None:
        future_plc_client = self._loop.create_future()
        self._plc_clients_by_nad[nad] = future_plc_client
        future_plc_client.set_result(plc_client)

    async def _autodetect(self, plc_info: PlcInfo) -> None:
        try:
            ip = await self._plc_detection_service.detect(plc_info.nad)
            self._plc_info_service.update(
                plc_info.nad, ip, None, PlcInfo.Origin.AUTO
            )
        except ExchangerTimeoutError:
            self._remove(plc_info.nad)
        except ScgiServerError as ex:
            self._remove(plc_info.nad)
            self._log.debug(lambda: f"{ex}")

    def _create_plc_client(self, plc_info: PlcInfo) -> PlcClient:
        return PlcClient(
            self._client_log,
            self._nad,
            plc_info,
            self._plc_activity_service,
            self._transaction_id_generator,
            MAX_FRAME_BYTES,
            self._exchanger,
            self._cpu_intensive_task_runner
        )
