from dataclasses import dataclass
from typing import List, Tuple, Dict

from lib.config.ini_config_parser import IniConfigParser
from mqtt_client.local.config.util import split_var_flatten, \
    split_map_dict


@dataclass(frozen=True)
class Subscriber:
    topic: str
    tags: Dict[str, List[str]]
    variables: List[str]
    accept_all_variables: bool


@dataclass(frozen=True)
class MqttSubscriberConfig:
    subscribers: List[Subscriber]

    def props(self) -> Tuple[List[Subscriber]]:
        return (
            self.subscribers,
        )

    @staticmethod
    def _create_subscriber(icp: IniConfigParser,
                           section: str,
                           section_idx: int) -> Subscriber:
        variables = split_var_flatten(
            icp.get_multisect_multival(section, section_idx, "var")
        )
        all_vars = any(v == "*" for v in variables)

        return Subscriber(
            topic=icp.get_multisect(section, section_idx, "topic"),
            tags=split_map_dict(
                icp.get_multisect_multival(section, section_idx, "map")
            ),
            variables=[] if all_vars else variables,
            accept_all_variables=all_vars
        )

    @classmethod
    def load(cls, icp: IniConfigParser, default: 'MqttSubscriberConfig'):
        section = "SUBSCRIBE"

        (
            subscribers,
        ) = default.props()

        section_count = icp.section_count(section)
        if section_count == 0:
            subs = subscribers
        else:
            subs = [
                cls._create_subscriber(icp, section, i)
                for i in range(section_count)
            ]

        return cls(
            subscribers=subs
        )
