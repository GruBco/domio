import asyncio

from lib.general.conditional_logger import ConditionalLogger
from lib.general.file_watcher import FileWatcher
from mqtt_client.local.input_output.websocket.client import WebSocketClient
from mqtt_client.local.mqtt_client import MqttClient
from mqtt_client.local.mqtt_hub import MqttHub


class MqttClientBootstrap:

    def __init__(self,
                 log: ConditionalLogger,
                 mqtt_client: MqttClient,
                 websocket_client: WebSocketClient,
                 websocket_keepalive: float,
                 mqtt_hub: MqttHub,
                 file_watcher: FileWatcher):
        self._log: ConditionalLogger = log
        self._mqtt_client: MqttClient = mqtt_client
        self._websocket_client: WebSocketClient = websocket_client
        self._websocket_keepalive: float = websocket_keepalive
        self._mqtt_hub: MqttHub = mqtt_hub
        self._file_watcher: FileWatcher = file_watcher

    async def run(self):
        # Give the SCGI server time to start before connecting.
        await asyncio.sleep(0.1)

        try:
            self._mqtt_client.start()

            await self._websocket_client.start()

            self._mqtt_hub.start()

            self._file_watcher.start()

            while True:
                if self._websocket_client.is_dead:
                    raise ConnectionError("Connection to SCGI server lost")

                await asyncio.sleep(1)
                    
        except ConnectionError as ex:
            self._log.error(f"SCGI connection error: {ex}")
            raise

        except Exception as ex:
            self._log.error(f"Error in MQTT client: {ex}")
            raise
