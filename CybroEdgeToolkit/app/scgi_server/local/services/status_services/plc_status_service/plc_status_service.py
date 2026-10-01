from typing import Dict

from scgi_server.local.services.plc_info_service.plc_info_service import \
    PlcInfoService
from scgi_server.local.services.rw_service.subservices.plc_activity_service \
    .plc_activity_service import PlcActivityService
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .alc_service.alc_service import AlcService
from scgi_server.local.services.status_services.plc_status_service \
    .single_plc_status_service import SinglePlcStatusService


class PlcStatusService:
    """Exposes status for all plcs
    """
    def __init__(self,
                 plc_info_service: PlcInfoService,
                 plc_activity_service: PlcActivityService,
                 alc_service: AlcService):
        self._plc_info_service: PlcInfoService = plc_info_service
        self._plc_activity_service: PlcActivityService = plc_activity_service
        self._plc_status_services: Dict[int, SinglePlcStatusService] = {}
        self._alc_service: AlcService = alc_service

    def __getitem__(self, nad) -> SinglePlcStatusService:
        try:
            return self._plc_status_services[nad]
        except KeyError:
            result = SinglePlcStatusService(
                nad,
                self._plc_info_service,
                self._plc_activity_service,
                self._alc_service
            )
            self._plc_status_services[nad] = result
            return result
