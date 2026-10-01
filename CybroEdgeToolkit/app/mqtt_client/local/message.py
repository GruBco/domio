import json
import time
from dataclasses import dataclass
from typing import Dict, Any

from mqtt_client.local.config.mqtt_client_config import MessageFormat
from mqtt_client.local.util import ValueType


class MessageGeneratorError(Exception):
    pass


@dataclass(frozen=True)
class SubscriberMessage:
    format: MessageFormat
    variables: Dict[str, ValueType]

    @property
    def has_data(self) -> bool:
        return len(self.variables) > 0

    def query_params(self) -> str:
        return "&".join(
            f"{k}={v}" for k, v in self.variables.items() if v is not None
        )


@dataclass(frozen=True)
class PublisherMessage:
    format: MessageFormat
    variables: Dict[str, ValueType]

    def _generate_legacy(self) -> str:
        # throw exception when no values are found
        if len(self.variables) == 0:
            raise ValueError("No value set for Message")
        # output one value for single value
        elif len(self.variables) == 1:
            val = list(self.variables.values())[0]
            return str(val) if val is not None else "null"
        # output CSV for multiple values
        else:
            return ",".join([
                str(value) if value is not None else "null"
                for value in self.variables.values()
            ])

    def _generate_home_assistant(self) -> str:
        return json.dumps(self.variables)

    def _generate_iconics(self) -> str:
        ts = int(time.time())
        records = [
            {
                "id": var,
                "v": val,
                "q": val is not None,
                "t": ts
            }
            for var, val in self.variables.items()
        ]
        return json.dumps(records)

    def _generate_senml(self) -> str:
        def _generate_senml_record(timestamp: int,
                                   variable: str,
                                   value: ValueType) -> Dict[str, Any]:

            r: Dict[str, Any] = {
                "n": variable,
                "t": timestamp
            }

            if value is not None:
                r["v"] = value
            else:
                r["vs"] = "invalid"

            return r

        ts = int(time.time())
        records = [
            _generate_senml_record(ts, var, val)
            for var, val in self.variables.items()
        ]
        return json.dumps(records)

    def generate_string(self) -> str:
        """Generates string from the current message for publishing on the MQTT
        topic.

        :return: Generated message.
        """
        if self.format == MessageFormat.LEGACY:
            return self._generate_legacy()
        elif self.format == MessageFormat.HOME_ASSISTANT:
            return self._generate_home_assistant()
        elif self.format == MessageFormat.ICONICS:
            return self._generate_iconics()
        elif self.format == MessageFormat.SENML_IETF:
            return self._generate_senml()
        else:
            raise MessageGeneratorError("Unrecognized message format")
