import selectors
from _asyncio import Task
from asyncio import AbstractEventLoop
from typing import List, Optional, Dict

from lib.general.conditional_logger import ConditionalLogger
from lib.general.selectable import Selectable
from lib.general.timer import Timer, Timestamp
from lib.input_output.scgi.scgi_client import ScgiClient
from mqtt_client.local.config.mqtt_client_config import MessageFormat
from mqtt_client.local.config.mqtt_publisher_config import Publisher
from mqtt_client.local.group.event_dispatcher import GroupsEventDispatcher
from mqtt_client.local.group.publisher_group import PublisherGroup
from mqtt_client.local.group.publisher_group_variable import \
    PublisherGroupVariable
from mqtt_client.local.mqtt_client import MqttClient
from mqtt_client.local.util import parse_xml


class PublisherGroups:
    def __init__(self,
                 log: ConditionalLogger,
                 loop: AbstractEventLoop,
                 scgi_client: ScgiClient,
                 mqtt_client: MqttClient,
                 message_format: MessageFormat):
        self._log = log
        self._loop: AbstractEventLoop = loop
        self._scgi_client: ScgiClient = scgi_client
        self._mqtt_client: MqttClient = mqtt_client
        self._message_format: MessageFormat = message_format

        self._groups: List[PublisherGroup] = []

        self._task_running: bool = False

        self._timer: Timer = Timer()
        self._task: Optional[Task] = None
        self._selector_stop: Selectable = Selectable()

        self._dispatcher: GroupsEventDispatcher = GroupsEventDispatcher(log, loop)

    @staticmethod
    def _convert_variables(tags: Dict[str, str],
                           variables: List[str]
                           ) -> List[PublisherGroupVariable]:
        return [PublisherGroupVariable(k, v) for k, v in tags.items()] + \
            [PublisherGroupVariable(None, v) for v in variables]

    def add_group(self,
                  read_period: int,
                  publish_period: int,
                  topic: str,
                  tags: Dict[str, str],
                  variables: List[str],
                  socket_id: Optional[int]) -> None:
        self._groups.append(
            PublisherGroup(
                log=self._log,
                loop=self._loop,
                scgi_client=self._scgi_client,
                dispatcher=self._dispatcher,
                message_format=self._message_format,
                read_period=read_period,
                publish_period=publish_period,
                topic=topic,
                variables=self._convert_variables(tags, variables),
                socket_id=socket_id
            )
        )

    def add_group_for_publisher(self, publisher: Publisher) -> None:
        self.add_group(
            read_period=publisher.read_period,
            publish_period=publisher.publish_period,
            topic=publisher.topic,
            tags=publisher.tags,
            variables=publisher.variables,
            socket_id=publisher.socket_id
        )

    def add_groups_for_publishers(self, publishers: List[Publisher]) -> None:
        for publisher in publishers:
            if publisher.read_period != 0 or publisher.socket_id is not None:
                self.add_group_for_publisher(publisher)

        for i, g in enumerate(self._groups):
            self._log.debug(f"Publisher {i} {g}")


    def _process_groups(self) -> None:
        """Process groups read and publish work.
        """
        for g in self._groups:
            if g.read_ticker.is_enabled():
                g.read_ticker.tick()
                if g.read_ticker.is_expired():
                    g.read()
                    g.read_ticker.reset()

            if g.publish_ticker.is_enabled():
                g.publish_ticker.tick()
                if g.publish_ticker.is_expired():
                    g.publish()
                    g.publish_ticker.reset()

            g.cleanup()

    def _publish_groups(self) -> None:
        """Publish groups changes to MQTT.
        """
        for g in self._groups:
            if g.is_changed:
                msg = g.get_message()
                if msg:
                    self._mqtt_client.publish(g.topic, msg.generate_string())
                g.unflag()

    async def _run_task(self):
        """Task for read timer.
        """
        s = selectors.DefaultSelector()
        s.register(self._timer, selectors.EVENT_READ)
        s.register(self._selector_stop, selectors.EVENT_READ)

        while self._task_running:
            events = await self._loop.run_in_executor(
                None,
                lambda: s.select()
            )
            for key, mask in events:
                if not (mask & selectors.EVENT_READ):
                    continue

                if key.fileobj == self._timer:
                    self._timer.clear_event()
                    self._process_groups()
                elif key.fileobj == self._selector_stop:
                    self._selector_stop.clear()
                    break
                else:
                    self._log.debug(f"Unknown event {key.fileobj}")

        s.unregister(self._timer)
        s.unregister(self._selector_stop)

    def start(self) -> None:
        self._task_running = True
        self._task = self._loop.create_task(self._run_task())

        self._dispatcher.start(
            self._publish_groups,
            self._publish_groups,
            self._publish_groups
        )

        self._timer.set_periodic(Timestamp(sec=1, nsec=0))

    def stop(self) -> None:
        self._task_running = False
        self._selector_stop.trigger()

        self._timer.stop()
        self._dispatcher.stop()

        if self._task is not None:
            self._task.cancel()
            self._task = None

    def handle_socket_message(self, msg: bytes) -> None:
        """Callback for handling socket message.

        :param msg: XML message in bytes.
        """
        try:
            parsed = parse_xml(msg.decode(), "event")

            if parsed.socket_id is not None:
                for g in self._groups:
                    g.handle_socket_message(parsed.socket_id,
                                            parsed.variables)
        except Exception as e:
            self._log.error(f"Error in socket message: {e}")
