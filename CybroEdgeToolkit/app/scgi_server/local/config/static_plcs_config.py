import re
from configparser import ParsingError
from dataclasses import dataclass
from typing import List

from lib.config.ini_config_parser import IniConfigParser
from scgi_server.local.config.static_plc_config import StaticPlcConfig
from lib.config.errors import ConfigError

section_pattern = re.compile(r'^c\d+$')


@dataclass(frozen=True)
class StaticPlcsConfig:
    static_plcs_configs: List[StaticPlcConfig]

    def __str__(self):
        header = "STATIC PLC CONFIG\n"
        plcs = "\n\n".join((str(plc) for plc in self.static_plcs_configs))

        return header + plcs

    @classmethod
    def load(cls, icp: IniConfigParser):
        try:
            return StaticPlcsConfig(
                [
                    StaticPlcConfig.load(icp, section)
                    for section in icp.section_names()
                    if is_section_static_plc(section)
                ]
            )
        except ParsingError as e:
            raise ConfigError("Can't read config file") from e


def is_section_static_plc(section: str) -> bool:
    return section_pattern.match(section) is not None
