import ssl
from typing import Callable, Optional, Tuple, List

from paho.mqtt.client import Client
# noinspection PyUnresolvedReferences
from paho.mqtt.enums import CallbackAPIVersion

from lib.general.conditional_logger import ConditionalLogger
from mqtt_client.local.config.mqtt_client_config import MessageFormat
from mqtt_client.local.config.mqtt_publisher_config import Publisher
from mqtt_client.local.config.mqtt_subscriber_config import Subscriber

MessageHandlerType = Optional[Callable[[str, str], None]]


class MqttClient:
    def __init__(self,  # noqa: S107 parameter count
                 log: ConditionalLogger,
                 ip: str,
                 port: int,
                 username: str,
                 password: str,
                 client_id: str,
                 version: int,
                 keepalive: int,
                 quality: int,
                 lwt: Optional[Tuple[str, str]],
                 tls_enabled: bool,
                 publisher_message_format: MessageFormat,
                 publishers: List[Publisher],
                 subscriber: List[Subscriber]):
        self._log: ConditionalLogger = log
        self._ip: str = ip
        self._port: int = port
        self._username: str = username
        self._password: str = password
        self._client_id: str = client_id
        self._version: int = version
        self._keepalive: int = keepalive
        self._quality: int = quality
        self._lwt: Optional[Tuple[str, str]] = lwt
        self._tls_enabled: bool = tls_enabled
        self._publisher_message_format: MessageFormat = \
            publisher_message_format

        self._subscribers: List[Subscriber] = subscriber
        # not used
        self._publishers: List[Publisher] = publishers

        self._client: Optional[Client] = None
        self._message_handler: MessageHandlerType = None

    def on_connect(self, client, userdata, flags, reason_code, properties):
        self._log.info(f"Connected to mqtt broker with result code "
                       f"{reason_code}")
        topics = list({
            (sub.topic, self._quality)
            for sub in self._subscribers
        })
        client.subscribe(topics)

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self._log.debug(f"Disconnected from mqtt broker with result code "
                        f"{reason_code}")

    def on_subscribe(self, client, userdata, mid, rc_list, properties):
        self._log.info(f"Subscribed with result code {rc_list}")

    def on_message(self, client, userdata, msg):
        self._log.debug(f"{msg.topic}: {msg.payload}")
        if self._message_handler is not None:
            if type(msg.payload) in [bytes, bytearray]:
                payload = msg.payload.decode()
            else:
                payload = str(msg.payload)
            self._message_handler(msg.topic, payload)

    def start(self):
        self._log.info('Starting MQTT client')
        self._client = Client(CallbackAPIVersion.VERSION2,
                              client_id=self._client_id,
                              clean_session=True,
                              protocol=self._version,
                              transport="tcp",
                              reconnect_on_failure=True,
                              manual_ack=False)

        # noinspection PyTypeChecker
        self._client.enable_logger(logger=self._log)

        self._client.on_connect = self.on_connect
        self._client.on_disconnect = self.on_disconnect
        self._client.on_subscribe = self.on_subscribe
        self._client.on_message = self.on_message

        if self._lwt is not None:
            self._client.will_set(topic=self._lwt[0],
                                  payload=self._lwt[1],
                                  qos=self._quality)

        self._client.username_pw_set(self._username, self._password)

        if self._tls_enabled:
            self._client.tls_set(cert_reqs=ssl.CERT_NONE)
            self._client.tls_insecure_set(True)

        self._client.connect(host=self._ip,
                             port=self._port,
                             keepalive=self._keepalive)

        self._client.loop_start()

    def stop(self):
        self._client.loop_stop()

    def publish(self, topic: str, value: str):
        self._log.debug(f"publish: {topic} {value}")
        msg_info = self._client.publish(topic, value, self._quality)
        msg_info.wait_for_publish()

    def set_message_handler(self, message_handler: MessageHandlerType) -> None:
        self._message_handler = message_handler
