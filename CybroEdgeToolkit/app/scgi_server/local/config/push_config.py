from dataclasses import dataclass
from datetime import timedelta
from typing import Tuple

from lib.config.ini_config_parser import IniConfigParser


@dataclass(frozen=True)
class PushConfig:
    enabled: bool
    timeout_h: timedelta

    @classmethod
    def create(cls,
               enabled: bool,
               timeout_h: timedelta):
        return cls(
            enabled,
            timeout_h
        )

    def props(self) -> Tuple[bool, timedelta]:
        return self.enabled, self.timeout_h

    @classmethod
    def load(cls, icp: IniConfigParser, default: 'PushConfig'):
        section = "PUSH"

        enabled, timeout_h = default.props()

        timeout = icp.get_int_optional(section, "timeout_h")
        if timeout is None:
            delta = timeout_h
        else:
            delta = timedelta(hours=timeout)

        return cls.create(
            icp.get_boolean(section, "enabled", enabled),
            delta
        )
