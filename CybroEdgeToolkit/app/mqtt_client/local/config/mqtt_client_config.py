from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional

from lib.config.ini_config_parser import IniConfigParser


class MessageFormat(Enum):
    LEGACY = 0
    HOME_ASSISTANT = 1
    ICONICS = 2
    SENML_IETF = 3


@dataclass(frozen=True)
class MqttClientConfig:
    ip: str
    port: int
    username: str
    password: str
    client_id: str
    version: int
    keepalive: int
    quality: int
    lwt: Optional[Tuple[str, str]]
    tls_enabled: bool
    message_format: MessageFormat

    def props(self) -> Tuple[
        str, int, str, str, str, int, int, int, Optional[Tuple[str, str]],
        bool, MessageFormat
    ]:
        return (
            self.ip,
            self.port,
            self.username,
            self.password,
            self.client_id,
            self.version,
            self.keepalive,
            self.quality,
            self.lwt,
            self.tls_enabled,
            self.message_format
        )

    @classmethod
    def load(cls, icp: IniConfigParser, default: 'MqttClientConfig'):
        section = "MQTT"

        (
            ip,
            port,
            username,
            password,
            client_id,
            version,
            keepalive,
            quality,
            lwt,
            tls_enabled,
            message_format
        ) = default.props()

        lwt_from_config_raw = icp.get_optional(section, "lwt")
        if lwt_from_config_raw is None:
            lwt_from_config = lwt
        else:
            raw = lwt_from_config_raw.split(",")
            lwt_from_config = (
                raw[0].lstrip(),
                raw[1].lstrip()
            )

        return cls(
            icp.get(section, "ip", ip),
            icp.get_int(section, "port", port),
            icp.get(section, "username", username),
            icp.get(section, "password", password),
            icp.get(section, "client_id", client_id),
            icp.get_int(section, "version", version),
            icp.get_int(section, "keepalive", keepalive),
            icp.get_int(section, "quality", quality),
            lwt_from_config,
            icp.get_boolean(section, "tls_enabled", tls_enabled),
            MessageFormat(
                icp.get_int(section, "message_format", message_format.value)
            )
        )
