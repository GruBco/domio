from asyncio import AbstractEventLoop
from typing import Optional

from lib.general.conditional_logger import get_logger
from lib.general.file_watcher import FileWatcher
from lib.general.paths import APP_DIR, CONFIG_FILE
from lib.input_output.scgi.scgi_client import ScgiClient
from lib.services.alias_service import AliasService
from mqtt_client.local.bootstrap import MqttClientBootstrap
from mqtt_client.local.config.config import Config
from mqtt_client.local.input_output.websocket.client import WebSocketClient
from mqtt_client.local.mqtt_hub import MqttHub
from mqtt_client.local.mqtt_client import MqttClient


class Container:
    def __init__(self,
                 config: Config,
                 main_loop: AbstractEventLoop,
                 communication_loop: AbstractEventLoop,
                 program_file_name: str):
        """Construct container and set explicit dependencies.

        """
        self.config: Config = config
        self.main_loop: AbstractEventLoop = main_loop
        self.communication_loop: AbstractEventLoop = communication_loop
        self.program_file_name: str = program_file_name

        self._mqtt_client: Optional[MqttClient] = None
        self._websocket_client: Optional[WebSocketClient] = None
        self._alias_service: Optional[AliasService] = None
        self._scgi_client: Optional[ScgiClient] = None
        self._mqtt_hub: Optional[MqttHub] = None
        self._file_watcher: Optional[FileWatcher] = None
        self._bootstrap: Optional[MqttClientBootstrap] = None

    @property
    def mqtt_client(self) -> MqttClient:
        if self._mqtt_client is None:
            self._mqtt_client = MqttClient(
                get_logger("CLIENT"),
                self.config.mqtt_client_config.ip,
                self.config.mqtt_client_config.port,
                self.config.mqtt_client_config.username,
                self.config.mqtt_client_config.password,
                self.config.mqtt_client_config.client_id,
                self.config.mqtt_client_config.version,
                self.config.mqtt_client_config.keepalive,
                self.config.mqtt_client_config.quality,
                self.config.mqtt_client_config.lwt,
                self.config.mqtt_client_config.tls_enabled,
                self.config.mqtt_client_config.message_format,
                self.config.mqtt_publisher_config.publishers,
                self.config.mqtt_subscriber_config.subscribers
            )

        # noinspection PyTypeChecker
        return self._mqtt_client

    @property
    def websocket_client(self) -> WebSocketClient:
        if self._websocket_client is None:
            self._websocket_client = WebSocketClient(
                get_logger("WEBSOCKET_CLIENT"),
                self.main_loop,
                self.config.scgi_config.server_address,
                self.config.scgi_config.scgi_port,
                self.config.scgi_config.tls_enabled,
                self.config.scgi_config.access_token,
                self.config.scgi_config.keepalive
            )

        # noinspection PyTypeChecker
        return self._websocket_client

    @property
    def alias_service(self) -> AliasService:
        if self._alias_service is None:
            self._alias_service = AliasService(
                self.config.alias_config.aliases,
                self.config.alias_config.reversed
            )

        # noinspection PyTypeChecker
        return self._alias_service

    @property
    def scgi_client(self) -> ScgiClient:
        if self._scgi_client is None:
            self._scgi_client = ScgiClient(
                get_logger("SCGI_CLIENT"),
                self.config.scgi_config.server_address,
                self.config.scgi_config.scgi_port,
                self.config.scgi_config.tls_enabled,
                self.config.scgi_config.access_token
            )

        # noinspection PyTypeChecker
        return self._scgi_client

    @property
    def mqtt_hub(self) -> MqttHub:
        if self._mqtt_hub is None:
            self._mqtt_hub = MqttHub(
                get_logger("MESSAGE_HUB"),
                self.alias_service,
                self.mqtt_client,
                self.websocket_client,
                self.scgi_client,
                self.main_loop,
                self.config.mqtt_publisher_config.publishers,
                self.config.mqtt_subscriber_config.subscribers,
                self.config.mqtt_client_config.message_format
            )

        # noinspection PyTypeChecker
        return self._mqtt_hub

    @property
    def file_watcher(self) -> FileWatcher:
        if self._file_watcher is None:
            log = get_logger("FILE_WATCHER")

            self._file_watcher = FileWatcher(
                CONFIG_FILE,
                lambda: FileWatcher.restart(log)
            )

        # noinspection PyTypeChecker
        return self._file_watcher

    @property
    def bootstrap(self) -> MqttClientBootstrap:
        if self._bootstrap is None:
            self._bootstrap = MqttClientBootstrap(
                get_logger("BOOTSTRAP"),
                self.mqtt_client,
                self.websocket_client,
                self.config.scgi_config.keepalive,
                self.mqtt_hub,
                self.file_watcher
            )

        # noinspection PyTypeChecker
        return self._bootstrap
