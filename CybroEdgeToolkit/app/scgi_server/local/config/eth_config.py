from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple, NewType

from lib.config.config.util.ip_resolver import \
    resolve_broadcast_address
from lib.config.ini_config_parser import IniConfigParser


class SocketDataType(Enum):
    BIT = 0
    UINT = 1
    LONG = 2


SocketsType = NewType(
    "SocketsType", Dict[int, Dict[SocketDataType, List[str]]]
)


@dataclass(frozen=True)
class EthConfig:
    bind_address: str
    port: int
    autodetect_enabled: bool
    autodetect_address: str
    sockets: SocketsType

    @classmethod
    def create(cls,
               bind_address: str,
               port: int,
               autodetect_enabled: bool,
               autodetect_address: str,
               sockets: SocketsType) -> 'EthConfig':
        return EthConfig(
            bind_address,
            port,
            autodetect_enabled,
            autodetect_address,
            sockets
        )

    def props(self) -> Tuple[str, int, bool, str, SocketsType]:
        return (
            self.bind_address,
            self.port,
            self.autodetect_enabled,
            self.autodetect_address,
            self.sockets
        )

    @classmethod
    def load(cls, icp: IniConfigParser, default: 'EthConfig'):
        section = "ETH"

        (
            bind_address,
            port,
            autodetect_enabled,
            autodetect_address,
            sockets
        ) = default.props()

        eth_bind_addr_from_conf = icp.get(
            section, "bind_address", bind_address
        )
        eth_auto_enabled_from_conf = icp.get_boolean(
            section, "autodetect_enabled", autodetect_enabled
        )
        eth_auto_addr_from_conf = icp.get(
            section, "autodetect_address", autodetect_address
        )

        if eth_bind_addr_from_conf == "":
            eth_bind_addr_from_conf = "0.0.0.0"

        if eth_auto_enabled_from_conf and eth_auto_addr_from_conf == "":
            eth_auto_addr_from_conf = resolve_broadcast_address()

        sockets_from_conf_raw = icp.get_multival(section, "socket")
        if sockets_from_conf_raw is None:
            sockets_from_conf_raw = sockets

        # noinspection PyTypeChecker
        sockets_from_conf: SocketsType = {}

        socket: str
        for socket in sockets_from_conf_raw:
            parts: List[List[str]] = [
                [item.strip() for item in parts.strip().split(",")]
                for parts in socket.strip().split(";")
            ]
            sockets_from_conf[int(parts[0][0])] = {
                SocketDataType.BIT: [x for x in parts[1] if x != ''],
                SocketDataType.UINT: [x for x in parts[2] if x != ''],
                SocketDataType.LONG: [x for x in parts[3] if x != '']
            }

        eth_port = icp.get_optional(section, "port")
        if eth_port is None or eth_port == "":
            eth_port = port
        else:
            eth_port = int(eth_port)

        return cls.create(
            eth_bind_addr_from_conf,
            eth_port,
            eth_auto_enabled_from_conf,
            eth_auto_addr_from_conf,
            sockets_from_conf
        )
