import uuid
from _asyncio import Task
from asyncio import AbstractEventLoop
from typing import List, Dict, Optional

from lib.general.conditional_logger import ConditionalLogger
from lib.input_output.scgi.scgi_client import ScgiClient
from mqtt_client.constants import MAX_GROUP_VARS
from mqtt_client.local.config.mqtt_client_config import MessageFormat
from mqtt_client.local.group.event_dispatcher import GroupsEventDispatcher
from mqtt_client.local.group.publisher_group_variable import \
    PublisherGroupVariable
from mqtt_client.local.group.ticker import Ticker
from mqtt_client.local.message import PublisherMessage
from mqtt_client.local.util import parse_xml


class PublisherGroup:
    def __init__(self,
                 log: ConditionalLogger,
                 loop: AbstractEventLoop,
                 scgi_client: ScgiClient,
                 dispatcher: GroupsEventDispatcher,
                 message_format: MessageFormat,
                 read_period: int,
                 publish_period: int,
                 topic: str,
                 variables: List[PublisherGroupVariable],
                 socket_id: Optional[int]):
        self._log: ConditionalLogger = log
        self._loop: AbstractEventLoop = loop
        self._scgi_client: ScgiClient = scgi_client
        self._dispatcher: GroupsEventDispatcher = dispatcher
        self._message_format: MessageFormat = message_format

        self._read_period: int = read_period
        self._publish_period: int = publish_period
        self._topic: str = topic
        self._variables: List[PublisherGroupVariable] = variables[:MAX_GROUP_VARS]
        self._socket_id: Optional[int] = socket_id

        self._data_changed: bool = False

        # cached query params
        self._query_params = "&".join(
            v.scgi_name for v in self._variables
        )

        self._read_ticker: Ticker = Ticker(self._read_period)
        self._publish_ticker: Ticker = Ticker(self._publish_period)

        self._read_tasks: Dict[str, Task] = {}

    def __repr__(self):
        return str({
            "read_period": self._read_period,
            "publish_period": self._publish_period,
            "topic": self._topic,
            "variables": self._variables,
            "socket_id": self._socket_id,
        })

    @property
    def read_ticker(self) -> Ticker:
        """Timeout ticker for read_period.

        :return: Ticker instance.
        """
        return self._read_ticker

    @property
    def publish_ticker(self) -> Ticker:
        """Timeout ticker for publish_period.

        :return: Ticker instance.
        """
        return self._publish_ticker

    @property
    def topic(self) -> str:
        """Group topic on which to publish changed values.

        :return: Name of the topic.
        """
        return self._topic

    @property
    def is_changed(self) -> bool:
        """Checks if a group has changed values.
        """
        return self._data_changed

    def get_message(self) -> Optional[PublisherMessage]:
        """Combines variables into a message object to pass to the MQTT client.

        :return: Message instance or None if there are no new values.
        """
        if self._data_changed:
            flagged = (v for v in self._variables if v.is_flagged())
            variables = {f.mqtt_name: f.value for f in flagged}
            message = PublisherMessage(self._message_format, variables)
            return message
        else:
            return None

    def flag(self) -> None:
        """Sets all changed flags to true.
        """
        for v in self._variables:
            v.flag()
        self._data_changed = True

    def unflag(self) -> None:
        """Sets all changed flags to false.
        """
        for v in self._variables:
            v.unflag()
        self._data_changed = False

    async def _update_variables(self) -> None:
        """Fetches variable values from the SCGI server.
        """
        try:
            xml = await self._scgi_client.get(self._query_params)
            values = parse_xml(xml, "data")

            for var, value in values.variables.items():
                for variable in self._variables:
                    if variable.scgi_name == var:
                        if variable.update(value):
                            self._data_changed = True
                            self._dispatcher.trigger_changed()

        except Exception as e:
            self._log.debug(f"Error in scgi message: {e}", exc_info=e)

    def read(self) -> None:
        """Queues task for updating of the variable values.
        """
        name = str(uuid.uuid4())

        self._read_tasks[name] = self._loop.create_task(
            self._update_variables(),
            name=name
        )

    def publish(self) -> None:
        """Flags all variables for publishing.
        """
        self.flag()
        self._dispatcher.trigger_publish()

    def cleanup(self) -> None:
        """Removes finished tasks from read task list.
        """
        self._read_tasks = {
            name: task
            for name, task in self._read_tasks.items()
            if task.done()
        }

    def handle_socket_message(self,
                              socket_id: int,
                              variables: Dict[str, str]) -> None:
        """Handles parsed socket message.

        :param socket_id: Socket ID for which data arrived.
        :param variables: variable name - value pairs parsed from XML received
        by the socket call
        """
        if self._socket_id is None or \
            self._socket_id != socket_id:
            return

        for name, value in variables.items():
            for variable in self._variables:
                if variable.scgi_name == name:
                    if variable.update(value):
                        self._data_changed = True

        if self._data_changed:
            self._log.debug(f"Publishing changed values: {self._variables}")
            self._dispatcher.trigger_socket()
