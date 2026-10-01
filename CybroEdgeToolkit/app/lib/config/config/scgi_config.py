from dataclasses import dataclass
from typing import Optional, Tuple

from lib.config.ini_config_parser import IniConfigParser


@dataclass(frozen=True)
class ScgiConfig:
    scgi_bind_address: str
    scgi_port: int
    reply_with_descriptions: bool
    tls_enabled: bool
    access_token: Optional[str]
    server_address: Optional[str]
    keepalive: float
    only_user_variables: bool

    def props(self) -> Tuple[
        str, int, bool, bool, Optional[str], Optional[str], float, bool
    ]:
        return (
            self.scgi_bind_address,
            self.scgi_port,
            self.reply_with_descriptions,
            self.tls_enabled,
            self.access_token,
            self.server_address,
            self.keepalive,
            self.only_user_variables
        )

    @classmethod
    def load(cls, icp: IniConfigParser, default: 'ScgiConfig'):
        section = "SCGI"

        (
            scgi_bind_address,
            scgi_port,
            reply_with_descriptions,
            tls_enabled,
            access_token,
            server_address,
            keepalive,
            only_user_variables
        ) = default.props()

        scgi_access_token_from_conf = icp.get_optional(
            section, "token", access_token
        )
        if scgi_access_token_from_conf == "":
            scgi_access_token_from_conf = None

        return cls(
            icp.get(section, "bind_address", scgi_bind_address),
            icp.get_int(section, "port", scgi_port),
            icp.get_boolean(section, "reply_with_descriptions", reply_with_descriptions),
            icp.get_boolean(section, "tls_enabled", tls_enabled),
            scgi_access_token_from_conf,
            icp.get(section, "server_address", server_address),
            icp.get_float(section, "keepalive", keepalive),
            icp.get_boolean(section, "only_user_variables", only_user_variables),
        )
