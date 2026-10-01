import re
from dataclasses import dataclass
from textwrap import dedent
from typing import Optional, Tuple

from lib.config.errors import InvalidPassword, InvalidPlcName
from lib.config.ini_config_parser import IniConfigParser


@dataclass(frozen=True)
class StaticPlcConfig:
    password: Optional[int]
    name: str
    ip: str
    port: int
    nad: int

    @classmethod
    def create(cls, password: str, name: str, ip: str, port: int):
        try:
            password = None if password == "" else int(password)
        except ValueError:
            raise InvalidPassword(password)

        return cls(password, name, ip, port, cls._extract_nad_from_name(name))

    def __str__(self):
        ip = self.ip if self.ip != "" else "_"

        return dedent(
            f"""\
                [{self.name}]
                  {ip}:{self.port}
                  password = {self.password}
                """
        )

    def props(self) -> Tuple[str, str, str, int]:
        return (
            "" if self.password is None else str(self.password),
            self.name,
            self.ip,
            self.port
        )

    @classmethod
    def load(cls, icp: IniConfigParser, section: str):
        return cls.create(
            icp.get(section, "password"),
            section,
            icp.get(section, "ip"),
            icp.get_int(section, "port")
        )

    @classmethod
    def _extract_nad_from_name(cls, name: str) -> int:
        match = re.search(r'^c(\d+)$', name)

        if match is None:
            raise InvalidPlcName(name)

        try:
            return int(match.group(1))
        except ValueError:
            raise InvalidPlcName(name)
