from datetime import timedelta
from pathlib import Path

from lib.config.config.alias_config import AliasConfig
from lib.config.config.debuglog_config import DebugLogConfig
from lib.config.config.locations_config import LocationsConfig
from lib.config.config.scgi_config import ScgiConfig
from lib.general.paths import APP_DIR
from scgi_server import Config
from scgi_server.local.config.abus_config import AbusConfig
from scgi_server.local.config.cache_config import CacheConfig
from scgi_server.local.config.eth_config import EthConfig
from scgi_server.local.config.push_config import PushConfig
from scgi_server.local.config.static_plcs_config import \
    StaticPlcsConfig

DEFAULT_CONFIG = Config(
    EthConfig(
        bind_address="0.0.0.0",
        port=0,
        autodetect_enabled=True,
        autodetect_address="",
        sockets={}
    ),
    PushConfig(
        enabled=False,
        timeout_h=timedelta(hours=24)
    ),
    AbusConfig(
        timeout_ms=timedelta(milliseconds=200),
        number_of_retries=3,
        password=None
    ),
    CacheConfig(
        request_period=timedelta(seconds=0),
        valid_period=timedelta(seconds=0),
        cleanup_period_s=timedelta(seconds=0)
    ),
    ScgiConfig(
        scgi_bind_address='',
        scgi_port=4000,
        reply_with_descriptions=True,
        tls_enabled=False,
        access_token=None,
        server_address=None,
        keepalive=.0,
        only_user_variables=False
    ),
    LocationsConfig(
        app_dir=APP_DIR,
        log_dir=Path("./log"),
        alc_dir=Path("./alc")
    ),
    DebugLogConfig(
        enabled=True,
        log_to_file=True,
        verbose_level="DEBUG",
        max_log_file_size_kb=1024,
        max_log_backup_count=5
    ),
    StaticPlcsConfig(
        static_plcs_configs=[]
    ),
    AliasConfig(
        aliases={}
    )
)
