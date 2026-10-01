import asyncio
import re
from typing import List, Dict, Iterator, Tuple

from lib.general.conditional_logger import ConditionalLogger
from lib.input_output.scgi.scgi_client import ScgiClient
from lib.services.alias_service import AliasService
from mqtt_client.local.config.mqtt_subscriber_config import Subscriber
from mqtt_client.local.group.subscriber_group import SubscriberGroup
from mqtt_client.local.group.topic import Topic
from mqtt_client.local.message import SubscriberMessage
from mqtt_client.local.message_parser import MessageParser


class SubscriberGroups:
    def __init__(self,
                 log: ConditionalLogger,
                 alias_service: AliasService,
                 scgi_client: ScgiClient):
        self._log: ConditionalLogger = log
        self._scgi_client: ScgiClient = scgi_client

        self._groups: List[SubscriberGroup] = []

        regex = (
            r'^(?:c\d{1,6}|(?:' +
            ("|".join(alias_service.aliases.keys())
             if alias_service is not None
             else "") +
            r'))\.[A-Za-z_][A-Za-z0-9_]{0,39}$'
        )
        self._pattern = re.compile(regex)

    def add_group(self,
                  topic: str,
                  tags: Dict[str, List[str]],
                  variables: List[str],
                  accept_all: bool):
        """Adds group from provided parameters.

        :param topic: Topic for which the groups should handle data.
        :param tags: Aliases for variables to search in message.
        :param variables: List of variables to search in message.
        :param accept_all: Whether to accept all received variables not in
        variables list.
        """
        self._groups.append(
            SubscriberGroup(
                topic=Topic(topic),
                tags=tags,
                variables=variables,
                accept_all_variables=accept_all
            )
        )

    def add_group_for_subscriber(self, subscriber: Subscriber) -> None:
        """Adds group from provided subscriber configuration.

        :param subscriber: Subscriber configuration.
        """
        self.add_group(
            topic=subscriber.topic,
            tags=subscriber.tags,
            variables=subscriber.variables,
            accept_all=subscriber.accept_all_variables
        )

    def add_groups_for_subscribers(self,
                                   subscribers: List[Subscriber]) -> None:
        """Adds groups from provided subscriber configurations.

        :param subscribers: List of subscriber configurations.
        """
        for s in subscribers:
            self.add_group_for_subscriber(s)

        for i, g in enumerate(self._groups):
            self._log.debug(f"Subscriber {i} {g}")

    def _find_groups_by_topic(self, topic: str) -> List[SubscriberGroup]:
        """Find all groups matching the topic.

        :param topic: Topic for which the groups should be found.
        """
        return [g for g in self._groups if g.topic.match_str(topic)]

    async def _scgi_get(self, query_params: Iterator[str]) -> Tuple[str]:
        """Update controllers with new values.

        :param query_params: Iterator of query parameters by which to make
        GET calls to SCGI server. For example `("a=1&b=2&c=3", "d=1&a=1")`.
        """
        return await asyncio.gather(*[
            self._scgi_client.get(params)
            for params in query_params
            if (params != '' and params != '&')
        ])

    def handle_mqtt_message(self, topic: str, payload: str) -> None:
        """Handles a received MQTT message.

        :param topic: MQTT topic on which the message arrived.
        :param payload: MQTT message payload.
        """
        msgs: List[SubscriberMessage] = []
        try:
            for g in self._find_groups_by_topic(topic):
                msgs.append(
                    MessageParser(
                        g.tags,
                        g.variables,
                        self._pattern if g.accept_all_variables else None,
                        payload
                    ).parse()
                )
        except Exception as e:
            self._log.error(f"Error parsing MQTT message: {e}")
            return

        try:
            asyncio.run(
                self._scgi_get((m.query_params() for m in msgs if m.has_data))
            )
        except Exception as e:
            self._log.error(f"Error sending message to SCGI: {e}")
