import struct
from dataclasses import dataclass
from typing import Optional, Union, List, Dict
from xml.etree.ElementTree import Element, SubElement, tostring

from scgi_server.local.config.eth_config import SocketsType, SocketDataType
from lib.services.alias_service import AliasService
from scgi_server.local.input_output.abus_stack.abus.abus_message import \
    AbusMessage
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .alc_service.var_info import VarInfo


# struct.unpack format and length of data for each SocketDataType
DATA_TYPE_PROPS = {
    SocketDataType.BIT: ("<B", 1),
    SocketDataType.UINT: ("<H", 2),
    SocketDataType.LONG: ("<I", 4)
}


@dataclass(frozen=True)
class SocketMessageVariable:
    name: str
    value: int
    description: Optional[str]


@dataclass(frozen=True)
class SocketMessage:
    """Creates socket message structure representation of received binary data.
    """
    nad: Union[str, int]
    socket: int
    variables: List[SocketMessageVariable]

    @classmethod
    def create(cls,
               abus_message: AbusMessage,
               alc_var_info: Dict[Union[int, str], VarInfo],
               socket_config: SocketsType) -> 'SocketMessage':
        """Creates new socket message instance.

        :param abus_message: ABUS message received for socket event.
        :param alc_var_info: Allocation table variables.
        :param socket_config: Sockets configuration.
        """
        nad = abus_message.from_nad
        socket = abus_message.command_frame.msg_type
        variables = []

        var_def = socket_config[socket]

        idx = 0
        for key in DATA_TYPE_PROPS.keys():
            for var in var_def[key]:
                fmt, length = DATA_TYPE_PROPS[key]
                data = abus_message.command_frame.body_bytes[idx:idx + length]
                try:
                    desc = alc_var_info[var].description
                except KeyError:
                    desc = None

                variables.append(SocketMessageVariable(
                    name=var,
                    value=struct.unpack(fmt, data)[0],
                    description=desc
                ))
                idx += length

        return cls(
            nad=nad,
            socket=socket,
            variables=variables
        )

    def to_xml(self, alias_service: AliasService) -> bytes:
        """Serializes a socket message to the event XML document.

        :param alias_service: Service for resolving controller aliases.
        :return: XML data
        """
        root = Element("event")

        socket_id = SubElement(root, "socket_id")
        socket_value = SubElement(socket_id, "value")
        socket_value.text = str(self.socket)

        for variable in self.variables:
            var = SubElement(root, "var")
            name = alias_service.to_alias_name(f"c{self.nad}.{variable.name}")

            SubElement(var, "name").text = name

            SubElement(var, "value").text = str(variable.value)
            if variable.description is not None:
                SubElement(var, "description").text = variable.description

        return tostring(root, encoding="utf-8", xml_declaration=True)
