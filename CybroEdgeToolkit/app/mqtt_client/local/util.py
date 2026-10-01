from dataclasses import dataclass
from typing import Dict, Optional, Union
from xml.etree.ElementTree import fromstring

ValueType = Optional[Union[int, float]]


@dataclass(frozen=True)
class ParsedXml:
    socket_id: Optional[int]
    variables: Dict[str, str]


def parse_xml(xml: str, root_tag: str) -> ParsedXml:
    """Parses XML data and extracts scgi variables and their values from
    it.

    :param xml: XML data to parse.
    :param root_tag: XML starting tag.
    :return: Dictionary containing variable name - value pairs.
    """
    root = fromstring(xml)
    if root.tag != root_tag:
        raise ValueError(f"No {root_tag} tag found in xml")

    values: Dict[str, str] = {}
    socket_id: Optional[int] = None

    socket = root.find("socket_id")
    if socket is not None:
        sock_id = socket.findtext("value")
        if sock_id is not None:
            socket_id = int(sock_id)

    for var in root.findall("var"):
        if var.tag != "var":
            raise ValueError("No var tag found in xml")

        name = var.findtext("name")
        if name is None:
            raise ValueError("No var name found in xml")
        value = var.findtext("value")
        if value is None:
            raise ValueError("No var value found in xml")

        values[name] = value

    return ParsedXml(
        socket_id=socket_id,
        variables=values,
    )


def int_or_float_value(value: str) -> ValueType:
    """Tries to convert a string value to float or integer value. If
    conversion fails, 'None' is returned.

    :param value: Value to convert.
    :return: None or converted numeric value.
    """
    v = None
    try:
        v = int(value)
    except ValueError:
        try:
            v = float(value)
        except ValueError:
            pass
    return v
