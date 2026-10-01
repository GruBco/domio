from pathlib import Path

from lib.config.config.alias_config import AliasConfig
from lib.config.config.debuglog_config import DebugLogConfig
from lib.config.config.locations_config import LocationsConfig
from mqtt_client.local.config.mqtt_client_config import \
    MqttClientConfig, MessageFormat
from mqtt_client.local.config.mqtt_publisher_config import \
    MqttPublisherConfig
from mqtt_client.local.config.mqtt_subscriber_config import \
    MqttSubscriberConfig
from lib.config.config.scgi_config import ScgiConfig
from lib.general.paths import APP_DIR
from mqtt_client.local.config.config import Config

DEFAULT_CONFIG = Config(
    ScgiConfig(
        scgi_bind_address='',
        scgi_port=4000,
        reply_with_descriptions=True,
        tls_enabled=False,
        access_token="",
        server_address=None,
        keepalive=5.0,
        only_user_variables=False
    ),
    LocationsConfig(
        app_dir=APP_DIR,
        log_dir=Path("./log"),
        alc_dir=Path("./alc")
    ),
    AliasConfig(
        aliases={}
    ),
    DebugLogConfig(
        enabled=True,
        log_to_file=True,
        verbose_level="DEBUG",
        max_log_file_size_kb=1024,
        max_log_backup_count=5
    ),
    MqttClientConfig(
        ip="",
        port=1883,
        username="",
        password="",
        client_id="cybrotech",
        version=2,
        keepalive=60,
        quality=0,
        lwt=None,
        tls_enabled=False,
        message_format=MessageFormat.HOME_ASSISTANT
    ),
    MqttPublisherConfig(
        publishers=[]
    ),
    MqttSubscriberConfig(
        subscribers=[]
    )
)
