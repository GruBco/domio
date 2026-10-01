from dataclasses import dataclass
from datetime import timedelta
from typing import Tuple

from lib.config.ini_config_parser import IniConfigParser


@dataclass(frozen=True)
class CacheConfig:
    request_period: timedelta
    valid_period: timedelta
    cleanup_period_s: timedelta

    @classmethod
    def create(cls,
               request_period_s: timedelta,
               valid_period_s: timedelta,
               cleanup_period_s: timedelta):
        return CacheConfig(
            request_period_s,
            valid_period_s,
            cleanup_period_s
        )

    def props(self) -> Tuple[timedelta, timedelta, timedelta]:
        return (
            self.request_period,
            self.valid_period,
            self.cleanup_period_s
        )

    @classmethod
    def load(cls, icp: IniConfigParser, default: 'CacheConfig'):
        section = "CACHE"

        request_period_s, valid_period_s, cleanup_period_s = default.props()

        request_period_conf = icp.get_int(section, "request_period_s")
        if request_period_conf is None:
            request_period = request_period_s
        else:
            request_period = timedelta(seconds=request_period_conf)

        valid_period_conf = icp.get_int(section, "valid_period_s")
        if valid_period_conf is None:
            valid_period = valid_period_s
        else:
            valid_period = timedelta(seconds=valid_period_conf)

        cleanup_period_conf = icp.get_int(section, "cleanup_period_s")
        if cleanup_period_conf is None:
            cleanup_period = cleanup_period_s
        else:
            cleanup_period = timedelta(seconds=cleanup_period_conf)

        return cls.create(
            request_period,
            valid_period,
            cleanup_period
        )
