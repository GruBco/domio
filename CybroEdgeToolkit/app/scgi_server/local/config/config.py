from configparser import ParsingError
from dataclasses import dataclass
from typing import Tuple

from lib.config.config.alias_config import AliasConfig
from lib.config.config.debuglog_config import DebugLogConfig
from lib.config.config.locations_config import LocationsConfig
from lib.config.config.scgi_config import ScgiConfig
from lib.config.errors import ConfigError
from lib.config.ini_config_parser import IniConfigParser
from scgi_server.local.config.abus_config import AbusConfig
from scgi_server.local.config.cache_config import CacheConfig
from scgi_server.local.config.eth_config import EthConfig
from scgi_server.local.config.push_config import PushConfig
from scgi_server.local.config.static_plcs_config import \
    StaticPlcsConfig


@dataclass(frozen=True)
class Config:
    eth_config: EthConfig
    push_config: PushConfig
    abus_config: AbusConfig
    cache_config: CacheConfig
    scgi_config: ScgiConfig
    locations_config: LocationsConfig
    debuglog_config: DebugLogConfig
    static_plcs_config: StaticPlcsConfig
    alias_config: AliasConfig

    def props(self) -> Tuple[
        EthConfig, PushConfig, AbusConfig, CacheConfig, ScgiConfig,
        LocationsConfig, DebugLogConfig, StaticPlcsConfig, AliasConfig
    ]:
        return (
            self.eth_config,
            self.push_config,
            self.abus_config,
            self.cache_config,
            self.scgi_config,
            self.locations_config,
            self.debuglog_config,
            self.static_plcs_config,
            self.alias_config
        )

    @classmethod
    def load(cls, parser: IniConfigParser, default: 'Config'):
        (
            eth_config,
            push_config,
            abus_config,
            cache_config,
            scgi_config,
            locations_config,
            debuglog_config,
            _,
            alias_config
        ) = default.props()

        try:
            return cls(
                EthConfig.load(parser, eth_config),
                PushConfig.load(parser, push_config),
                AbusConfig.load(parser, abus_config),
                CacheConfig.load(parser, cache_config),
                ScgiConfig.load(parser, scgi_config),
                LocationsConfig.load(parser, locations_config),
                DebugLogConfig.load(parser, debuglog_config),
                StaticPlcsConfig.load(parser),
                AliasConfig.load(parser, alias_config)
            )
        except ParsingError as e:
            raise ConfigError("Can't read config file") from e
        except ConfigError as e:
            raise ConfigError(e)
