from typing import Optional

from mqtt_client.local.util import ValueType
from mqtt_client.local.util import int_or_float_value


class PublisherGroupVariable:
    def __init__(self, tag: Optional[str], name: str):
        self._tag: Optional[str] = tag
        self._name: str = name
        self._value: ValueType = None
        self._send_req: bool = False

    def __repr__(self):
        return str({
            'tag': self._tag,
            'name': self._name,
            'value': self._value,
            'send_req': self._send_req
        })

    @property
    def mqtt_name(self) -> str:
        return self._name if self._tag is None else self._tag

    @property
    def scgi_name(self) -> str:
        return self._name

    @property
    def tag(self) -> Optional[str]:
        return self._tag

    @property
    def value(self) -> ValueType:
        return self._value

    def update(self, value: str) -> bool:
        """Updates the value with the provided string value. A value must be
        number, otherwise the value is set to None.

        :param value: A string representation of the number value to set.
        :return: True if the value has been changed, False if it wasn't.
        """
        v = int_or_float_value(value)

        if self._value != v:
            self._value = v
            self._send_req = True

        return self._send_req

    def flag(self) -> None:
        """Flags the variable for sending.
        """
        self._send_req = True

    def unflag(self) -> None:
        """Removes a sending flag from the variable.
        """
        self._send_req = False

    def is_flagged(self) -> bool:
        """Returns whether the variable is flagged for sending or not.
        """
        return self._send_req
