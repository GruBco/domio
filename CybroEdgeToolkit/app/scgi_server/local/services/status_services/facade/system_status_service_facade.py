import asyncio
from typing import Coroutine, Callable, List, Tuple, Dict

from lib.general.util import humanize_timedelta, tabulate
from lib.input_output.scgi.r_response import RResponse
from scgi_server.local.services.rw_service.scgi_communication.rw_request \
    import RWRequest
from scgi_server.local.services.status_services.system_status_service \
    import SystemStatusService


class SystemStatusServiceFacade:
    """Public interface for `SystemStatusService`
    """
    def __init__(self, system_status_service: SystemStatusService):
        self._system_status_service: SystemStatusService = (
            system_status_service
        )

        self._actions: Dict[
            str,
            Tuple[Callable[[], Coroutine[None, None, str]], str]
        ] = {
            "scgi_status": (
                self._scgi_status,
                "SCGI status is 'active', otherwise the server is down."
            ),
            "server_version": (
                self._server_version,
                "Server version, 'major.minor.release'."
            ),
            "server_uptime": (
                self._server_uptime,
                "Time since the server is started, 'xx days, hh:mm:ss'."
            ),
            "scgi_request_count": (
                self._scgi_request_count,
                "Total number of requests since startup."
            ),
            "push_port_status": (
                self._push_port_status,
                "Push port status can be 'active', 'inactive' or 'error'."
            ),
            "push_count": (
                self._push_count,
                "Total number of push messages received from controllers."
            ),
            "push_ack_errors": (
                self._push_ack_errors,
                "Total number of push acknowledge errors."
            ),
            "push_list_count": (
                self._push_list_count,
                "Total number of controllers in push list."
            ),
            "push_list": (
                self._push_list,
                "Formated list of controllers that are sending push message to the server."
            ),
            "nad_list": (
                self._nad_list,
                "List of available controllers, push and autodetect together."
            ),
            "cache_valid": (
                self._cache_valid,
                "Cache validity time in seconds."
            ),
            "cache_request": (
                self._cache_request,
                "Cache request time in seconds."
            ),
            "udp_rx_count": (
                self._udp_rx_count,
                "Total number of received UDP packets."
            ),
            "udp_tx_count": (
                self._udp_tx_count,
                "Total number of transmitted UDP packets."
            )
        }

    async def process(self, requests: List[RWRequest]) -> List[RResponse]:
        coroutines = (self._process_request(request) for request in requests)
        responses = await asyncio.gather(*coroutines)
        return list(responses)

    async def _process_request(self, request: RWRequest) -> RResponse:
        try:
            (value, description) = await self.get(request.tag_name)
            return RResponse.create(
                request.name, request.tag_name, value, description
            )
        except KeyError:
            return RResponse.create(
                request.name, request.tag_name, code=RResponse.Code.UNKNOWN
            )

    async def get(self, tag_name: str) -> Tuple[str, str]:
        action, description = self._actions[tag_name]
        value = await action()
        return value, description

    async def _scgi_status(self) -> str:
        return self._system_status_service.scgi_status

    async def _server_version(self) -> str:
        return self._system_status_service.server_version

    async def _server_uptime(self) -> str:
        return humanize_timedelta(
            self._system_status_service.server_uptime.total_seconds()
        )

    async def _scgi_request_count(self) -> str:
        return str(self._system_status_service.scgi_request_count)

    async def _push_port_status(self) -> str:
        if self._system_status_service.is_push_port_active:
            return "active"
        else:
            return "inactive"

    async def _push_count(self) -> str:
        return str(
            self._system_status_service.successful_push_acknowledgments_count
        )

    async def _push_ack_errors(self) -> str:
        return str(
            self._system_status_service.failed_push_acknowledgments_count
        )

    async def _push_list_count(self) -> str:
        return str(self._system_status_service.push_plcs_count)

    async def _push_list(self) -> str:
        column_width = SystemStatusService.PushPlcInfo.column_width()
        headers = SystemStatusService.PushPlcInfo.header()
        data = [
            item.to_string_list()
            for item in self._system_status_service.push_plc_info_table
        ]

        table = tabulate(
            column_width, headers, data, " ", False
        )

        return table

    async def _nad_list(self) -> List[str]:
        return [
            str(nad) for nad in await self._system_status_service.get_plcs()
        ]

    async def _cache_valid(self) -> str:
        return str(self._system_status_service.cache_valid_period.seconds)

    async def _cache_request(self) -> str:
        return str(self._system_status_service.cache_request_period.seconds)

    async def _udp_rx_count(self) -> str:
        return str(self._system_status_service.udp_rx_count)

    async def _udp_tx_count(self) -> str:
        return str(self._system_status_service.udp_tx_count)
