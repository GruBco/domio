from enum import Enum, auto


class LoggerNames(Enum):
    TCP = auto()
    UDP = auto()
    PUSH = auto()
    ABUS = auto()
    PLC_INFO = auto()
    PLC_CLIENT = auto()
    PLC_COMM = auto()
    ALC = auto()
    SCGI_SERVER = auto()
    PLC_DETECT = auto()
    SOCKET = auto()
    ALIAS_SERVICE = auto()
    FILE_WATCHER = auto()
