from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict

from scgi_server.local.services.plc_info_service.errors import \
    PlcInfoNotFoundError
from scgi_server.local.services.plc_info_service.plc_info import PlcInfo
from scgi_server.local.services.plc_info_service.plc_info_service import \
    PlcInfoService
from scgi_server.local.services.rw_service.subservices \
    .plc_activity_service.plc_activity import PlcActivity
from scgi_server.local.services.rw_service.subservices.plc_activity_service \
    .plc_activity_service import PlcActivityService
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .alc_service.alc_service import AlcService
from scgi_server.local.services.rw_service.subservices.plc_comm_service. \
    alc_service.var_info import VarInfo
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .plc_client_manager.plc_client.status import PlcStatus


class SinglePlcStatusService:
    """Exposes status for specific plc.
    """
    def __init__(self,
                 nad: int,
                 plc_info_service: PlcInfoService,
                 plc_activity_service: PlcActivityService,
                 alc_service: AlcService):
        self._nad: int = nad
        self._plc_info_service: PlcInfoService = plc_info_service
        self._plc_activity_service: PlcActivityService = plc_activity_service
        self._alc_service: AlcService = alc_service

    @property
    def timestamp(self) -> Optional[datetime]:
        try:
            return self.plc_info.program_datetime
        except PlcInfoNotFoundError:
            return None

    @property
    def ip_port(self) -> Optional[Tuple[Optional[str], int]]:
        try:
            plc_info = self.plc_info
            return plc_info.ip, plc_info.port
        except PlcInfoNotFoundError:
            return None

    @property
    def response_time(self) -> Optional[timedelta]:
        return self.plc_activity.last_exchange_duration

    @property
    def has_alc(self) -> bool:
        return self.plc_activity.last_used_alc_crc is not None

    @property
    def device_status(self) -> PlcActivity.DeviceStatus:
        return self.plc_activity.device_status

    @property
    def plc_status(self) -> Optional[PlcStatus]:
        return self.plc_activity.last_plc_status

    @property
    def bytes_transferred(self) -> int:
        return self.plc_activity.bytes_transferred

    async def get_alc_text(self) -> Optional[str]:
        crc = self.plc_activity.last_used_alc_crc
        if crc is not None:
            return await self._alc_service.load_alc_text_for_crc(crc)
        else:
            return None

    async def get_alc_data(self) -> Optional[Dict[str, VarInfo]]:
        crc = self.plc_activity.last_used_alc_crc
        if crc is not None:
            return self._alc_service[crc]
        else:
            return None

    @property
    def communication_error_count(self) -> int:
        return self.plc_activity.failed_exchanges_count

    @property
    def plc_info(self) -> PlcInfo:
        return self._plc_info_service.get_plc_info(self._nad)

    @property
    def plc_activity(self) -> PlcActivity:
        return self._plc_activity_service[self._nad]
