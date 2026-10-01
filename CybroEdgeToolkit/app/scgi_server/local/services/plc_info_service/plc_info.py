from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Tuple


@dataclass
class PlcInfo:
    """Data about connected controller.
    Note: This record is deleted when push timeout_h is exceeded. Deletion is
    done by PlcInfoCleaner service. Only controllers originating from push and
    autodetect service are deleted.
    """
    class Origin(Enum):
        STATIC = "STATIC"
        PUSH = "PUSH"
        AUTO = "AUTO"
        PROXY = 'PROXY'

    # Date and time when record was created.
    created: datetime
    # Origin from which controller information is acquired (static config,
    # autodetect, push).
    origin: Origin
    # Controller's identifier.
    nad: int
    # Controller's ip address.
    ip: Optional[str]
    # Controller's communication port.
    port: int
    # Password for accessing controller, if required.
    password: Optional[int]
    # Controller's program update date and time.
    program_datetime: Optional[datetime]
    # Date and time when this record was updated.
    last_update_time: datetime

    @property
    def has_ip(self) -> bool:
        return self.ip is not None

    @property
    def has_password(self) -> bool:
        return self.password is not None

    def props(self) -> Tuple[
        datetime, Origin, int, Optional[str], int, Optional[int], datetime
    ]:

        return (
            self.created,
            self.origin,
            self.nad,
            self.ip,
            self.port,
            self.password,
            self.last_update_time
        )

    def __str__(self):
        ip_str = self.ip if self.has_ip else "?"

        result = f"{self.origin.name} c{self.nad} {ip_str}:{self.port}"

        if self.password is not None:
            result += f" password={self.password}"

        if self.program_datetime is not None:
            result += f" program={self.program_datetime}"

        return result
