from configparser import ParsingError
from dataclasses import dataclass
from typing import Tuple

from lib.config.config.alias_config import AliasConfig
from lib.config.config.debuglog_config import DebugLogConfig
from lib.config.config.locations_config import LocationsConfig
from lib.config.config.scgi_config import ScgiConfig
from lib.config.errors import ConfigError
from lib.config.ini_config_parser import IniConfigParser
from mqtt_client.local.config.mqtt_client_config import \
    MqttClientConfig
from mqtt_client.local.config.mqtt_publisher_config import \
    MqttPublisherConfig
from mqtt_client.local.config.mqtt_subscriber_config import \
    MqttSubscriberConfig


@dataclass(frozen=True)
class Config:
    scgi_config: ScgiConfig
    locations_config: LocationsConfig
    alias_config: AliasConfig
    debuglog_config: DebugLogConfig
    mqtt_client_config: MqttClientConfig
    mqtt_publisher_config: MqttPublisherConfig
    mqtt_subscriber_config: MqttSubscriberConfig

    def props(self) -> Tuple[
        ScgiConfig, LocationsConfig, AliasConfig, DebugLogConfig,
        MqttClientConfig, MqttPublisherConfig, MqttSubscriberConfig
    ]:
        return (
            self.scgi_config,
            self.locations_config,
            self.alias_config,
            self.debuglog_config,
            self.mqtt_client_config,
            self.mqtt_publisher_config,
            self.mqtt_subscriber_config
        )

    @classmethod
    def load(cls, parser: IniConfigParser, default: 'Config'):
        (
            scgi_config,
            locations_config,
            alias_config,
            debuglog_config,
            mqtt_client_config,
            mqtt_publisher_config,
            mqtt_subscriber_config
        ) = default.props()

        try:
            return cls(
                ScgiConfig.load(parser, scgi_config),
                LocationsConfig.load(parser, locations_config),
                AliasConfig.load(parser, alias_config),
                DebugLogConfig.load(parser, debuglog_config),
                MqttClientConfig.load(parser, mqtt_client_config),
                MqttPublisherConfig.load(parser, mqtt_publisher_config),
                MqttSubscriberConfig.load(parser, mqtt_subscriber_config)
            )
        except ParsingError as e:
            raise ConfigError("Can't read config file") from e
        except ValueError as e:
            raise ConfigError(e)
