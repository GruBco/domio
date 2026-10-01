from asyncio import AbstractEventLoop
from typing import List

from lib.general.conditional_logger import ConditionalLogger
from lib.input_output.scgi.scgi_client import ScgiClient
from lib.services.alias_service import AliasService
from mqtt_client.local.config.mqtt_client_config import MessageFormat
from mqtt_client.local.config.mqtt_publisher_config import Publisher
from mqtt_client.local.config.mqtt_subscriber_config import Subscriber
from mqtt_client.local.group.publisher_groups import PublisherGroups
from mqtt_client.local.group.subscriber_groups import SubscriberGroups
from mqtt_client.local.input_output.websocket.client import WebSocketClient
from mqtt_client.local.mqtt_client import MqttClient


class MqttHub:
    def __init__(self,
                 log: ConditionalLogger,
                 alias_service: AliasService,
                 mqtt_client: MqttClient,
                 websocket_client: WebSocketClient,
                 scgi_client: ScgiClient,
                 loop: AbstractEventLoop,
                 publishers: List[Publisher],
                 subscribers: List[Subscriber],
                 message_format: MessageFormat):
        self._log: ConditionalLogger = log
        self._mqtt_client: MqttClient = mqtt_client
        self._websocket_client: WebSocketClient = websocket_client
        self._publishers: List[Publisher] = publishers
        self._subscribers: List[Subscriber] = subscribers

        self._publisher_groups: PublisherGroups = PublisherGroups(
            log=log,
            loop=loop,
            scgi_client=scgi_client,
            mqtt_client=mqtt_client,
            message_format=message_format
        )
        self._subscriber_groups: SubscriberGroups = SubscriberGroups(
            log=log,
            alias_service=alias_service,
            scgi_client=scgi_client
        )

    def _init(self) -> None:
        self._publisher_groups.add_groups_for_publishers(self._publishers)
        self._subscriber_groups.add_groups_for_subscribers(self._subscribers)

    def _register_callbacks(self) -> None:
        self._websocket_client.set_data_handler(
            self._publisher_groups.handle_socket_message
        )
        self._mqtt_client.set_message_handler(
            self._subscriber_groups.handle_mqtt_message
        )

    def _unregister_callback(self) -> None:
        self._websocket_client.set_data_handler(None)
        self._mqtt_client.set_message_handler(None)

    def start(self) -> None:
        """Starts message hub.
        """
        self._log.info("Starting message hub")
        self._init()
        self._register_callbacks()
        self._publisher_groups.start()

    def stop(self) -> None:
        """Stops message hub.
        """
        self._log.info("Stopping message hub")
        self._publisher_groups.stop()
        self._unregister_callback()
