import asyncio
from itertools import chain
from typing import Generator, Coroutine, Optional, List, Dict, Tuple, Union

from lib.input_output.scgi.r_var_response import RVarResponse
from lib.input_output.scgi.r_response import RResponse
from lib.services.cpu_intensive_task_runner import \
    CPUIntensiveTaskRunner
from scgi_server.local.input_output.abus_stack.abus.abus_exchanger import \
    AbusExchanger
from scgi_server.local.services.rw_service.scgi_communication.rw_request \
    import RWRequest
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .plc_comm_service import PlcCommService
from scgi_server.local.services.status_services.facade \
    .plc_status_service_facade import PlcStatusServiceFacade
from scgi_server.local.services.status_services.facade \
    .system_status_service_facade import SystemStatusServiceFacade


class RWService:
    def __init__(
            self,
            system_status_service_facade: SystemStatusServiceFacade,
            plc_status_service_facade: PlcStatusServiceFacade,
            plc_communication_service: PlcCommService,
            cpu_intensive_task_runner: CPUIntensiveTaskRunner
    ):
        self._system_status_service: SystemStatusServiceFacade = (
            system_status_service_facade
        )
        self._plc_status_service: PlcStatusServiceFacade = (
            plc_status_service_facade
        )
        self._plc_communication_service: PlcCommService = (
            plc_communication_service
        )
        self._cpu_intensive_task_runner: CPUIntensiveTaskRunner = (
            cpu_intensive_task_runner
        )

    def set_exchanger(self, exchanger: AbusExchanger) -> None:
        self._plc_communication_service.set_exchanger(exchanger)

    async def on_rw_requests(self,
                             r_requests: Optional[List[RWRequest]] = None,
                             w_requests: Optional[List[RWRequest]] = None,
                             task_id: Optional[int] = None) -> List[RResponse]:
        if r_requests is None:
            r_requests = []
        if w_requests is None:
            w_requests = []

        sys_status_r_requests: List[RWRequest]
        plc_status_r_requests: List[RWRequest]
        plc_r_requests: List[RWRequest]
        (
            sys_status_r_requests,
            plc_status_r_requests,
            plc_r_requests
        ) = await self._cpu_intensive_task_runner.run(
            self._classify_read_requests_by_target,
            r_requests
        )

        plc_status_r_requests_by_nad: Dict[int, List[RWRequest]]
        plc_r_requests_by_nad: Dict[int, List[RWRequest]]
        plc_w_requests_by_nad: Dict[int, List[RWRequest]]
        plc_var_status_r_requests_by_nad: Dict[int, List[RWRequest]]
        (
            plc_status_r_requests_by_nad,
            plc_r_requests_by_nad,
            plc_w_requests_by_nad
        ) = (
            await self._cpu_intensive_task_runner.run(
                self._group_requests_by_nad,
                plc_status_r_requests
            ),
            await self._cpu_intensive_task_runner.run(
                self._group_requests_by_nad,
                plc_r_requests
            ),
            await self._cpu_intensive_task_runner.run(
                self._group_requests_by_nad,
                w_requests
            )
        )

        sys_status_responses: List[RResponse]
        plc_status_responses: List[RResponse]
        plc_responses: List[RResponse]
        (
            sys_status_responses,
            plc_status_responses,
            plc_responses
        ) = await asyncio.gather(
            self._process_sys_status_read_requests(sys_status_r_requests),
            self._process_plc_status_read_requests(
                plc_status_r_requests_by_nad
            ),
            self._process_plc_requests(
                plc_r_requests_by_nad, plc_w_requests_by_nad, task_id
            )
        )

        return sys_status_responses + plc_status_responses + plc_responses

    @staticmethod
    def _classify_read_requests_by_target(
        requests: List[RWRequest]
    ) -> Tuple[
        List[RWRequest],
        List[RWRequest],
        List[RWRequest]
    ]:
        """Separates requests by type onto list of system request,
        list of plc system requests and plc requests.
        """
        sys_status_requests: List[RWRequest] = []
        plc_status_requests: List[RWRequest] = []
        plc_requests: List[RWRequest] = []

        for request in requests:
            if request.target == RWRequest.Target.SYSTEM:
                sys_status_requests.append(request)
            elif request.target == RWRequest.Target.PLC_SYSTEM:
                plc_status_requests.append(request)
            elif request.target == RWRequest.Target.PLC:
                plc_requests.append(request)

        return (
            sys_status_requests,
            plc_status_requests,
            plc_requests
        )

    @staticmethod
    def _group_requests_by_nad(requests: List[RWRequest]
                               ) -> Dict[int, List[RWRequest]]:
        result = {}

        for request in requests:
            nad = request.nad
            try:
                requests_for_nad = result[nad]
            except KeyError:
                requests_for_nad = []
                result[nad] = requests_for_nad

            requests_for_nad.append(request)

        return result

    async def _process_sys_status_read_requests(self,
                                                requests: List[RWRequest]):
        return await self._system_status_service.process(requests)

    async def _process_plc_status_read_requests(
        self,
        requests_by_nad: Dict[int, List[RWRequest]]
    ) -> List[Union[RResponse, RVarResponse]]:
        coroutines = (
            self._plc_status_service.process(nad, requests)
            for nad, requests in requests_by_nad.items()
        )
        lists_of_responses = await asyncio.gather(*coroutines)
        responses = chain(*lists_of_responses)
        return list(responses)

    async def _process_plc_requests(
        self,
        r_requests_by_nad: Dict[int, List[RWRequest]],
        w_requests_by_nad: Dict[int, List[RWRequest]],
        task_id: int
    ) -> List[RResponse]:
        coroutines = self._generate_coroutines_for_plc_requests(
            r_requests_by_nad,
            w_requests_by_nad,
            task_id
        )

        lists_of_responses: Tuple[List[RResponse], ...] = \
            await asyncio.gather(*coroutines)

        responses: chain[RResponse] = chain(*lists_of_responses)

        return list(responses)

    def _generate_coroutines_for_plc_requests(
        self,
        r_requests_by_nad: Dict[int, List[RWRequest]],
        w_requests_by_nad: Dict[int, List[RWRequest]],
        task_id: Optional[int]
    ) -> Generator[Coroutine[None, None, List[RResponse]], None, None]:
        for nad, r_requests in r_requests_by_nad.items():
            w_requests = w_requests_by_nad.get(nad, [])
            yield (
                self._plc_communication_service.process_rw_requests(
                    nad,
                    r_requests,
                    w_requests,
                    task_id
                )
            )
