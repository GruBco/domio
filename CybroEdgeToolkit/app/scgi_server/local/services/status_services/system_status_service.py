from dataclasses import dataclass
from datetime import timedelta, datetime
from typing import List, Tuple, Optional

from scgi_server.local.services.rw_service.subservices.plc_comm_service.plc_client_manager.plc_client.status import \
    PlcStatus
from scgi_server.constants import APP_VERSION
from scgi_server.local.input_output.abus_stack.udp.udp_activity_service \
    import UdpActivityService
from scgi_server.local.input_output.scgi.scgi_activity_service import \
    ScgiActivityService
from scgi_server.local.services.plc_info_service.plc_info import PlcInfo
from scgi_server.local.services.plc_info_service.plc_info_service import \
    PlcInfoService
from scgi_server.local.services.push_service.push_activity_service import \
    PushActivityService
from scgi_server.local.services.rw_service.subservices.plc_activity_service \
    .plc_activity_service import PlcActivityService
from scgi_server.local.services.status_services.plc_status_service \
    .plc_status_service import PlcStatusService


class SystemStatusService:
    @dataclass(frozen=True)
    class PushPlcInfo:
        last_update: datetime
        nad: int
        origin: PlcInfo.Origin
        ip_port: Tuple[str, int]
        status: Optional[PlcStatus]
        program: bool
        alc: bool
        program_sent: Optional[datetime]
        response: Optional[timedelta]

        @staticmethod
        def header() -> List[str]:
            return [
                "push received",
                "nad",
                "type",
                "ip address:port",
                "status",
                "program",
                "alc",
                "program sent",
                "response"
            ]

        @staticmethod
        def column_width() -> List[int]:
            return [
                19,
                5,
                6,
                21,
                7,
                7,
                7,
                19,
                8
            ]

        def _get_last_update_string(self) -> str:
            return (
                self.last_update.strftime("%Y-%m-%d %H:%M:%S")
                if self.origin != PlcInfo.Origin.STATIC
                else ""
            )

        def _get_host_port_string(self) -> str:
            return (f"{self.ip_port[0] if self.ip_port[0] else ''}"
                    f":{self.ip_port[1]}")

        def _get_status_string(self) -> str:
            if self.status == PlcStatus.STOP:
                status = "stop"
            elif self.status == PlcStatus.PAUSE :
                status = "pause"
            elif self.status == PlcStatus.RUN:
                status = "run"
            elif self.status == PlcStatus.NO_VALID_PROGRAM:
                status = "no pgm"
            elif self.status == PlcStatus.SCAN_OVERRUN_ERROR:
                status = "so err"
            else:
                status = ""

            return status

        def _get_program_sent_string(self) -> str:
            return (
                self.program_sent.strftime("%Y-%m-%d %H:%M:%S")
                if self.program_sent
                else ""
            )

        def _get_response_time_string(self) -> str:
            return (str(int(self.response.microseconds / 1000.0))
                    if self.response
                    else "")

        def to_string_list(self) -> List[str]:
            return [
                self._get_last_update_string(),
                str(self.nad),
                self.origin.value.lower(),
                self._get_host_port_string(),
                self._get_status_string(),
                "ok" if self.program else "",
                "ok" if self.alc else "",
                self._get_program_sent_string(),
                self._get_response_time_string()
            ]

    def __init__(self,
                 plc_info_service: PlcInfoService,
                 push_activity_service: PushActivityService,
                 scgi_activity_service: ScgiActivityService,
                 plc_activity_service: PlcActivityService,
                 udp_activity_service: UdpActivityService,
                 plc_status_service: PlcStatusService,
                 cache_valid_period: timedelta,
                 cache_request_period: timedelta,
                 push_enabled: bool):
        self._plc_info_service = plc_info_service
        self._push_activity_service = push_activity_service
        self._scgi_activity_service = scgi_activity_service
        self._plc_activity_service = plc_activity_service
        self._udp_activity_service = udp_activity_service
        self._app_version = APP_VERSION
        self._plc_status_service = plc_status_service
        self._cache_valid_period: timedelta = cache_valid_period
        self._cache_request_period: timedelta = cache_request_period
        self._push_enabled: bool = push_enabled

    @property
    def scgi_status(self) -> str:
        return "active"

    @property
    def scgi_request_count(self) -> int:
        return self._scgi_activity_service.requests_received_count

    @property
    def server_version(self) -> str:
        return self._app_version

    @property
    def server_uptime(self) -> timedelta:
        return self._scgi_activity_service.server_uptime

    @property
    def cache_valid_period(self) -> timedelta:
        return self._cache_valid_period

    @property
    def cache_request_period(self) -> timedelta:
        return self._cache_request_period

    @property
    def is_push_port_active(self) -> bool:
        return self._push_enabled

    @property
    def push_plcs_count(self) -> int:
        return len(list(self._plc_info_service.get_plc_infos()))

    @property
    def failed_push_acknowledgments_count(self) -> int:
        return self._push_activity_service.failed_push_acknowledgments_count

    @property
    def successful_push_acknowledgments_count(self) -> int:
        return self._push_activity_service.successful_push_acknowledgments_count

    async def get_plcs(self) -> List[int]:
        return [plc_info.nad for plc_info in
                self._plc_info_service.get_plc_infos()]

    @property
    def push_plc_info_table(self) -> List[PushPlcInfo]:
        """Gets data for controllers originating from push service.
        """
        result = []
        for plc_info in self._plc_info_service.get_plc_infos():
            nad = plc_info.nad

            plc_status_service = self._plc_status_service[nad]
            plc_info = plc_status_service.plc_info

            result.append(SystemStatusService.PushPlcInfo(
                last_update=plc_info.last_update_time,
                nad=nad,
                origin=plc_info.origin,
                ip_port=(plc_info.ip, plc_info.port),
                status=plc_status_service.plc_status,
                program=plc_info.program_datetime is not None,
                alc=plc_status_service.has_alc,
                program_sent=plc_info.program_datetime,
                response=plc_status_service.response_time
            ))

        return result

    @property
    def udp_rx_count(self) -> int:
        return self._udp_activity_service.rx_count

    @property
    def udp_tx_count(self) -> int:
        return self._udp_activity_service.tx_count

    @property
    def plc_info_table(self):
        result = []
        for plc_info in self._plc_info_service.get_plc_infos():
            nad = plc_info.nad
            plc_activity = self._plc_activity_service[nad]
            initiated_exchanges_count = plc_activity.initiated_exchanges_count
            failed_exchanges_count = plc_activity.failed_exchanges_count
            last_failed_exchange_time = plc_activity.last_failed_exchange_time
            ip = plc_info.ip
            port = plc_info.port
            origin = plc_info.origin

            row = (
                nad,
                initiated_exchanges_count,
                failed_exchanges_count,
                None if last_failed_exchange_time is None
                else last_failed_exchange_time.strftime("%d-%m-%y %H:%M:%S"),
                ip,
                port,
                origin.value
            )
            result.append(row)

        return result
