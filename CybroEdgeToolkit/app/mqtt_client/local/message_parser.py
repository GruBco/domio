import json
import re
from typing import Dict, List, Optional, Union

from mqtt_client.local.config.mqtt_client_config import MessageFormat
from mqtt_client.local.message import SubscriberMessage
from mqtt_client.local.util import ValueType, int_or_float_value


class MessageParserError(Exception):
    pass


class MessageParser:
    def __init__(self,
                 tags: Dict[str, List[str]],
                 variables: List[str],
                 variable_test_pattern: Optional[re.Pattern],
                 payload: str):
        self._tags: Dict[str, List[str]] = tags
        self._variables: List[str] = variables
        self._variable_test_pattern: Optional[re.Pattern] = \
            variable_test_pattern
        self._payload: str = payload

        self._json: Optional[Union[List, Dict]]
        try:
            self._json = json.loads(payload)
        except json.decoder.JSONDecodeError:
            self._json = None

    def _is_cybro_variable(self, value: str) -> bool:
        """When accept all variables is enabled it checks if value is
        matching cybro variable naming format.

        :param value: Value to test.
        :return: True if accept all variables is enabled and value matches
        cybro variable naming format.
        """
        return self._variable_test_pattern is not None and \
            self._variable_test_pattern.match(value) is not None

    def _is_legacy_format(self) -> bool:
        """Since single value is valid JSON, check only if payload doesn't
        begin with '{' or '[' character.

        :returns: True if payload is in legacy format.
        """
        return not (
            self._payload.startswith("{") or self._payload.startswith("[")
        )

    def _is_legacy_single(self) -> bool:
        """Checks if payload contains single value in legacy formatting.

        :return: True if payload is single value legacy format.
        """
        return self._payload == "null" or \
            int_or_float_value(self._payload) is not None

    def _detect_json_format(self) -> Optional[MessageFormat]:
        """Detect JSON message format.

        :return: One of the supproted formats or None for unrecognized format.
        """
        if self._json is None:
            return None

        if isinstance(self._json, list):
            if len(self._json) > 0 and isinstance(self._json[0], dict):
                if "n" in self._json[0]:
                    return MessageFormat.SENML_IETF
                elif "id" in self._json[0]:
                    return MessageFormat.ICONICS
        elif isinstance(self._json, dict):
            if "n" in self._json:
                return MessageFormat.SENML_IETF
            elif "id" in self._json:
                return MessageFormat.ICONICS
            else:
                return MessageFormat.HOME_ASSISTANT

        return None

    def _parse_legacy_single_message(self) -> SubscriberMessage:
        value = int_or_float_value(self._payload)
        return SubscriberMessage(
            format=MessageFormat.LEGACY,
            variables=dict.fromkeys(self._variables, value)
        )

    def _parse_legacy_csv_message(self) -> SubscriberMessage:
        values = [
            int_or_float_value(v.strip()) for v in self._payload.split(",")
        ]
        values_len = len(values)

        var_values = {}
        for i in range(len(self._variables)):
            if i >= values_len:
                break
            var_values[self._variables[i]] = values[i]

        return SubscriberMessage(
            format=MessageFormat.LEGACY,
            variables=var_values
        )

    def _parse_home_assistant_message(self) -> SubscriberMessage:
        vs: Dict[str, ValueType] = {}

        if not isinstance(self._json, dict):
            raise MessageParserError("Failed to parse Home Assistant message")

        for k in self._json.keys():
            if k in self._tags:
                for var in self._tags[k]:
                    vs[var] = self._json[k]
            elif k in self._variables:
                vs[k] = self._json[k]
            elif self._is_cybro_variable(k):
                vs[k] = self._json[k]

        return SubscriberMessage(
            format=MessageFormat.HOME_ASSISTANT,
            variables=vs
        )

    def _parse_iconics_record(self, rec: Dict) -> Dict[str, ValueType]:
        vs: Dict[str, ValueType] = {}
        var_name = rec["id"]

        if var_name in self._tags:
            for var in self._tags[var_name]:
                vs[var] = rec["v"]

        if var_name in self._variables:
            vs[var_name] = rec["v"]

        if self._is_cybro_variable(var_name):
            vs[var_name] = rec["v"]

        return vs

    def _parse_iconics_message(self) -> SubscriberMessage:
        vs: Dict[str, ValueType] = {}

        if isinstance(self._json, list):
            for rec in self._json:
                vs.update(self._parse_iconics_record(rec))
        elif isinstance(self._json, dict):
            vs.update(self._parse_iconics_record(self._json))
        else:
            raise MessageParserError("Failed to parse Iconics message")

        return SubscriberMessage(
            format=MessageFormat.ICONICS,
            variables=vs
        )

    def _parse_senml_record(self, rec: Dict) -> Dict[str, ValueType]:
        vs: Dict[str, ValueType] = {}
        var_name = rec["n"]

        def resolve_value(variable: str):
            if "v" in rec:
                vs[variable] = rec["v"]
            elif "vs" in rec and rec["vs"] == "invalid":
                vs[variable] = None

        if var_name in self._tags:
            for var in self._tags[var_name]:
                resolve_value(var)

        if var_name in self._variables:
            resolve_value(var_name)

        if self._is_cybro_variable(var_name):
            resolve_value(var_name)

        return vs

    def _parse_senml_message(self) -> SubscriberMessage:
        vs: Dict[str, ValueType] = {}

        if isinstance(self._json, list):
            for rec in self._json:
                vs.update(self._parse_senml_record(rec))
        elif isinstance(self._json, dict):
            vs.update(self._parse_senml_record(self._json))
        else:
            raise MessageParserError("Failed to parse SenML message")

        return SubscriberMessage(
            format=MessageFormat.SENML_IETF,
            variables=vs
        )

    def parse(self) -> SubscriberMessage:
        if self._is_legacy_format():
            if self._is_legacy_single():
                return self._parse_legacy_single_message()
            else:
                return self._parse_legacy_csv_message()
        else:
            fmt = self._detect_json_format()
            if fmt == MessageFormat.HOME_ASSISTANT:
                return self._parse_home_assistant_message()
            elif fmt == MessageFormat.ICONICS:
                return self._parse_iconics_message()
            elif fmt == MessageFormat.SENML_IETF:
                return self._parse_senml_message()

        raise MessageParserError("Unrecognized payload type")
