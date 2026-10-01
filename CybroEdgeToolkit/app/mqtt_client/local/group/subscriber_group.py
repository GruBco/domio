from dataclasses import dataclass
from typing import Dict, List

from mqtt_client.local.group.topic import Topic


@dataclass(frozen=True)
class SubscriberGroup:
    topic: Topic
    tags: Dict[str, List[str]]
    variables: List[str]
    accept_all_variables: bool

    def __repr__(self):
        return str({
            "topic": self.topic,
            "tags": self.tags,
            "variables": self.variables,
            "accept_all_variables": self.accept_all_variables
        })
