from dataclasses import dataclass
from typing import Tuple

from scgi_server.local.input_output.abus_stack.abus.command_frame import \
    CommandFrame, Direction, CommandFrameUtil, Type
from scgi_server.local.input_output.abus_stack.abus.transport_frame \
    import TransportFrameUtil
from scgi_server.local.input_output.abus_stack.udp.udp_message \
    import UdpMessage


@dataclass()
class AbusMessage:
    addr: Tuple[str, int]
    from_nad: int
    to_nad: int
    transaction_id: int
    command_frame: CommandFrame

    @property
    def ip(self) -> str:
        return self.addr[0]

    @property
    def port(self) -> int:
        return self.addr[1]

    @property
    def size(self) -> int:
        return TransportFrameUtil.HEADER_LENGTH + \
               TransportFrameUtil.TRANSACTION_ID_LENGTH + \
               TransportFrameUtil.CRC_LENGTH + self.command_frame.size

    def __str__(self):
        (host, port) = self.addr
        return (f"{host}:{port} {self.from_nad} -> "
                f"{self.to_nad} [{self.transaction_id}] {self.command_frame}")

    @property
    def is_push(self) -> bool:
        return \
            self.to_nad == 0 and \
            self.command_frame.msg_direction == Direction.ACK and \
            self.command_frame.msg_type == Type.COMMAND.value

    @property
    def is_socket(self) -> bool:
        return (
            self.to_nad == 0 and
            self.command_frame.msg_direction == Direction.ACK and
            self.command_frame.msg_type != Type.COMMAND.value
        )

    @property
    def is_broadcast(self) -> bool:
        return \
            self.to_nad == 0 and \
            self.command_frame.msg_direction == Direction.ACK and \
            self.command_frame.msg_type == Type.BROADCAST.value


class AbusMessageUtil:
    @classmethod
    def abus_msg_to_udp_msg(cls, abus_msg: AbusMessage) -> UdpMessage:
        transport_frame_bytes = AbusMessageUtil.abus_msg_to_bytes(abus_msg)
        return UdpMessage(transport_frame_bytes, abus_msg.addr)

    @classmethod
    def abus_msg_to_bytes(cls, abus_msg: AbusMessage) -> bytes:
        command_frame = abus_msg.command_frame
        command_frame_bytes = CommandFrameUtil.command_frame_to_bytes(
            command_frame
        )
        transport_frame = TransportFrameUtil.create_transport_frame(
            abus_msg.from_nad,
            abus_msg.to_nad,
            command_frame_bytes,
            abus_msg.transaction_id
        )
        transport_frame_bytes = TransportFrameUtil.transport_frame_to_bytes(
            transport_frame
        )

        return transport_frame_bytes

    @classmethod
    def udp_msg_to_abus_msg(cls, udp_msg: UdpMessage) -> AbusMessage:
        return cls.create_abus_msg_from_bytes(udp_msg.data, udp_msg.addr)

    @classmethod
    def create_abus_msg_from_bytes(cls,
                                   transport_frame_bytes: bytes,
                                   address: Tuple[str, int]) -> AbusMessage:
        transport_frame = TransportFrameUtil.bytes_to_transport_frame(
            transport_frame_bytes
        )
        command_frame_bytes = transport_frame.data_block_bytes
        command_frame = CommandFrameUtil.bytes_to_command_frame(
            command_frame_bytes
        )

        return AbusMessage(
            address,
            transport_frame.from_addr,
            transport_frame.to_addr,
            transport_frame.transaction_id,
            command_frame
        )
