from asyncio import AbstractEventLoop
from itertools import chain
from typing import Optional, List, Dict

from lib.general.conditional_logger import ConditionalLogger
from lib.general.misc import create_task_callback
from lib.input_output.scgi.r_response import RResponse
from lib.services.cpu_intensive_task_runner import \
    CPUIntensiveTaskRunner
from scgi_server.local.data_logger.data_logger_cache import DataLoggerCache
from scgi_server.local.general.errors import ExchangerTimeoutError
from scgi_server.local.general.unzip import unzip
from scgi_server.local.input_output.abus_stack.abus.abus_exchanger import \
    AbusExchanger
from scgi_server.local.services.plc_info_service.plc_info_service import \
    PlcInfoService
from scgi_server.local.services.rw_service.scgi_communication.rw_request \
    import RWRequest
from scgi_server.local.services.rw_service.subservices.plc_activity_service \
    .plc_activity_service import PlcActivityService
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .alc_service.alc_service import AlcService
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .alc_service.var_info import VarInfo
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .plc_cache.plc_cache import PlcCache
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .plc_cache.plc_cache_facade import PlcCacheFacade
from scgi_server.local.services.rw_service.subservices \
    .plc_comm_service.plc_client_manager.plc_client.plc_client import PlcClient
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .plc_client_manager.plc_client_manager import PlcClientManager
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .plc_communicator import PlcCommunicator


class PlcCommService:
    def __init__(
        self,
        log: ConditionalLogger,
        plc_info_service: PlcInfoService,
        alc_service: AlcService,
        plc_activity_service: PlcActivityService,
        plc_client_manager: PlcClientManager,
        plc_cache: PlcCache,
        data_logger_cache: DataLoggerCache,
        cpu_intensive_task_runner: CPUIntensiveTaskRunner,
        only_user_variables: bool,
        loop: AbstractEventLoop
    ):
        self._log: ConditionalLogger = log
        self._plc_info_service: PlcInfoService = plc_info_service
        self._alc_service: AlcService = alc_service
        self._plc_activity_service: PlcActivityService = plc_activity_service
        self._plc_client_manager: PlcClientManager = plc_client_manager
        self._cache: PlcCache = plc_cache
        self._data_logger_cache: DataLoggerCache = data_logger_cache
        self._cpu_intensive_task_runner: CPUIntensiveTaskRunner = (
            cpu_intensive_task_runner
        )
        self._only_user_variables: bool = only_user_variables
        self._loop: AbstractEventLoop = loop

    def set_exchanger(self, exchanger: AbusExchanger):
        self._plc_client_manager.set_exchanger(exchanger)

    async def process_rw_requests(self,
                                  nad: int,
                                  r_requests: List[RWRequest],
                                  w_requests: List[RWRequest],
                                  task_id: int) -> List[RResponse]:
        responses = await self._process_rw_requests(
            nad, r_requests, w_requests, task_id
        )
        self._log.debug(
            lambda: f"RW Results c{nad} - {len(responses)} responses"
        )
        return responses

    async def _process_rw_requests(self,
                                   nad: int,
                                   r_requests: List[RWRequest],
                                   w_requests: List[RWRequest],
                                   task_id: Optional[int]) -> List[RResponse]:
        plc_client = await self._plc_client_manager.get(nad)

        if plc_client is None or not plc_client.plc_info.has_ip:
            return [
                RResponse.create(
                    request.name,
                    request.tag_name,
                    request.value,
                    "",
                    False,
                    RResponse.Code.DEVICE_NOT_FOUND
                )
                for request in r_requests
            ]

        if self._cache is None:
            cache_facade = None
        else:
            cache_facade = PlcCacheFacade(self._log, self._cache[nad])

        plc_communicator = PlcCommunicator(
            self._log,
            plc_client,
            cache_facade,
            self._plc_activity_service,
            self._get_alc,
            self._update_plc_client_datetime,
            self._update_plc_client_ip,
            self._cpu_intensive_task_runner,
            self._data_logger_cache,
            self._only_user_variables
        )

        if task_id is not None:
            if len(w_requests) > 0:
                # sanity check
                self._log.error(f"{len(w_requests)} write requests came from "
                                f"the data logger. They will be ignored.")
            return await plc_communicator.process_r_requests_for_data_logger(
                r_requests,
                task_id
            )

        if len(w_requests) > 0:
            return await plc_communicator.process_rw_requests(r_requests,
                                                              w_requests)

        if cache_facade is None:
            return await plc_communicator.process_rw_requests(r_requests,
                                                              [])
        else:
            cache_result = await cache_facade.read(r_requests)

            responses = list(chain(
                cache_result.fresh.values(),
                cache_result.stinky.values()
            ))
            postponable_requests = list(cache_result.stinky.keys())
            urgent_requests = list(cache_result.not_available)

        if len(postponable_requests) > 0:
            self._log.debug("Fetch postponable")
            (
                self._loop.create_task(plc_communicator.process_rw_requests(
                    postponable_requests, []
                ))
                .add_done_callback(create_task_callback(self._log))
            )

        if len(urgent_requests) > 0:
            responses += await plc_communicator.process_rw_requests(
                urgent_requests, []
            )

        return responses

    async def _get_alc(self,
                       plc_client: PlcClient,
                       crc: int) -> Optional[Dict[str, VarInfo]]:
        try:
            return self._alc_service[crc]
        except KeyError:
            pass

        try:
            self._log.info(lambda: f"New crc for c{plc_client.plc_info.nad}: "
                                   f"{crc}. Reload alc...")
            await self._fetch_alc_and_save(plc_client, crc)
            return self._alc_service[crc]
        except ExchangerTimeoutError:
            return None

    async def _fetch_alc_and_save(self, plc_client: PlcClient, crc: int):
        alc_bytes_zipped = await plc_client.fetch_alc_file()
        alc_bytes = await unzip(alc_bytes_zipped)
        alc_text = alc_bytes.decode("latin-1")
        self._alc_service.set_alc_text(alc_text, crc)

    async def _update_plc_client_datetime(self, plc_client, program_datetime):
        nad = plc_client.plc_info.nad
        self._plc_info_service.update_program_datetime(nad, program_datetime)
        return await self._plc_client_manager.get(nad)

    async def _update_plc_client_ip(
        self,
        plc_client: PlcClient
    ) -> Optional[PlcClient]:
        # deleting and requesting plc_info will implicitly trigger ip detection
        nad = plc_client.plc_info.nad
        await self._plc_info_service.remove_plc_info(nad)
        return await self._plc_client_manager.get(nad)

    async def get_crc(self, nad: int) -> Optional[int]:
        plc_client = await self._plc_client_manager.get(nad)

        if plc_client is None or not plc_client.plc_info.has_ip:
            return None

        if self._cache is None:
            cache_facade = None
        else:
            cache_facade = PlcCacheFacade(self._log, self._cache[nad])

        plc_communicator = PlcCommunicator(
            self._log,
            plc_client,
            cache_facade,
            self._plc_activity_service,
            self._get_alc,
            self._update_plc_client_datetime,
            self._update_plc_client_ip,
            self._cpu_intensive_task_runner,
            self._data_logger_cache,
            self._only_user_variables
        )

        return await plc_communicator.plc_head_check()
