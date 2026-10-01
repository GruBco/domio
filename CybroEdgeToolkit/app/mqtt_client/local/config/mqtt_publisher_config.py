from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

from lib.config.ini_config_parser import IniConfigParser
from mqtt_client.local.config.util import split_var_flatten, split_map_dict_one


@dataclass(frozen=True)
class Publisher:
    read_period: int
    publish_period: int
    topic: str
    tags: Dict[str, str]
    variables: List[str]
    socket_id: Optional[int]


@dataclass(frozen=True)
class MqttPublisherConfig:
    publishers: List[Publisher]

    def props(self) -> Tuple[List[Publisher]]:
        return (
            self.publishers,
        )

    @classmethod
    def load(cls, icp: IniConfigParser, default: 'MqttPublisherConfig'):
        section = "PUBLISH"

        (
            publishers,
        ) = default.props()

        count = icp.section_count(section)
        if count == 0:
            pubs = publishers
        else:
            pubs = [
                Publisher(
                    read_period=icp.get_int_multisect(
                        section, i, "read_period"
                    ),
                    publish_period=icp.get_int_multisect(
                        section, i, "publish_period"
                    ),
                    topic=icp.get_multisect(section, i, "topic"),
                    tags=split_map_dict_one(
                        icp.get_multisect_multival(section, i, "map")
                    ),
                    variables=split_var_flatten(
                        icp.get_multisect_multival(section, i, "var")
                    ),
                    socket_id=icp.get_int_multisect_optional(
                        section, i, "socket_id"
                    )
                ) for i in range(count)
            ]

        return cls(
            publishers=pubs
        )
