from dataclasses import dataclass
from typing import Tuple

from lib.config.ini_config_parser import IniConfigParser


@dataclass(frozen=True)
class DebugLogConfig:
    enabled: bool
    log_to_file: bool
    verbose_level: str
    max_log_file_size_kb: int
    max_log_backup_count: int

    @classmethod
    def create(cls,
               enabled: bool,
               log_to_file: bool,
               verbose_level: str,
               max_log_file_size_kb: int,
               max_log_backup_count: int):
        return DebugLogConfig(
            enabled,
            log_to_file,
            verbose_level,
            max_log_file_size_kb,
            max_log_backup_count
        )

    def props(self) -> Tuple[bool, bool, str, int, int]:
        return (
            self.enabled,
            self.log_to_file,
            self.verbose_level,
            self.max_log_file_size_kb,
            self.max_log_backup_count
        )

    @classmethod
    def load(cls, icp: IniConfigParser, default: 'DebugLogConfig'):
        section = "DEBUGLOG"

        (
            enabled,
            log_to_file,
            verbose_level,
            max_log_file_size_kb,
            max_log_backup_count,
        ) = default.props()

        return cls.create(
            icp.get_boolean(section, "enabled", enabled),
            icp.get_boolean(section, "log_to_file", log_to_file),
            icp.get(section, "verbose_level", verbose_level),
            icp.get_int(section, "max_file_size_kb", max_log_file_size_kb),
            icp.get_int(section, "max_backup_count", max_log_backup_count)
        )
