from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Tuple, Union

from lib.config.errors import InvalidPassword
from lib.config.ini_config_parser import IniConfigParser


@dataclass(frozen=True)
class AbusConfig:
    timeout_ms: timedelta
    number_of_retries: int
    password: Optional[int]

    @classmethod
    def create(cls,
               timeout_ms: timedelta,
               number_of_retries: int,
               password: Union[int, str]):
        try:
            password = None if password == "" else int(password)
        except ValueError:
            raise InvalidPassword(str(password))

        return cls(
            timeout_ms,
            number_of_retries,
            password,
        )

    def props(self) -> Tuple[timedelta, int, str]:
        return (
            self.timeout_ms,
            self.number_of_retries,
            "" if self.password is None else str(self.password),
        )

    @classmethod
    def load(cls, icp: IniConfigParser, default: 'AbusConfig'):
        section = "ABUS"

        (
            timeout_ms,
            number_of_retries,
            password,
        ) = default.props()

        timeout_ms_conf = icp.get_int_optional(section, "timeout_ms")
        if timeout_ms_conf is None:
            tms = timeout_ms
        else:
            tms = timedelta(milliseconds=timeout_ms_conf)

        return cls.create(
            tms,
            icp.get_int(
                section, "number_of_retries", number_of_retries
            ),
            icp.get(section, "password", password),
        )
