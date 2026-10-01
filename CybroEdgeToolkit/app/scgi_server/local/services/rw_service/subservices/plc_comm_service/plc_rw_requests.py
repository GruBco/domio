from dataclasses import dataclass
from typing import List, Dict

from scgi_server.local.services.rw_service.subservices.plc_comm_service.plc_rw_request \
    import PlcRWRequest


@dataclass()
class PlcRWRequests:
    def __init__(self):
        self._one_byte: Dict[PlcRWRequest, bool] = {}
        self._two_byte: Dict[PlcRWRequest, bool] = {}
        self._four_byte: Dict[PlcRWRequest, bool] = {}
        self._invalid: Dict[PlcRWRequest, bool] = {}

    @property
    def has_valid(self) -> bool:
        return (
            len(self._one_byte) == 0 and
            len(self._two_byte) == 0 and
            len(self._four_byte) == 0
        )

    @property
    def one_byte(self) -> List[PlcRWRequest]:
        return list(self._one_byte.keys())

    @property
    def two_byte(self) -> List[PlcRWRequest]:
        return list(self._two_byte.keys())

    @property
    def four_byte(self) -> List[PlcRWRequest]:
        return list(self._four_byte.keys())

    @property
    def invalid(self) -> List[PlcRWRequest]:
        return list(self._invalid.keys())

    def add(self, request: PlcRWRequest) -> None:
        if request.is_valid:
            self._add_valid(request)
        else:
            self._invalid[request] = True

    def _add_valid(self, request: PlcRWRequest) -> None:
        size = request.alc_data.size

        try:
            self._get_valid_dict(size)[request] = True
        except KeyError:
            self._invalid[request] = True

    def _get_valid_dict(self, size: int) -> Dict[PlcRWRequest, bool]:
        if size == 1:
            return self._one_byte
        elif size == 2:
            return self._two_byte
        elif size == 4:
            return self._four_byte
        else:
            raise KeyError

    def __str__(self):
        return (f"{len(self.one_byte)}, {len(self.two_byte)}, "
                f"{len(self.four_byte)} (1B, 2B, 4B)")
