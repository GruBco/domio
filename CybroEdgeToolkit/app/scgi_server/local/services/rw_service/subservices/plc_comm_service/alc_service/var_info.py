from dataclasses import dataclass

from scgi_server.local.services.rw_service.subservices \
    .plc_comm_service.data_type import DataType


@dataclass(frozen=True)
class VarInfo:
    # Attr [1]
    id: int
    # Name [7]
    name: str
    # Array [2] > 1
    is_array: bool
    # Array [2]
    array_size: int
    # Addr [0]
    address: int
    # Offset [3]
    offset: int
    # Size [4]
    size: int
    # Scope [5]
    scope: str
    # Type [6]
    data_type: DataType
    # [8]
    description: str

    def __str__(self) -> str:
        return f"{self.name}: id={self.id}, is_array={self.is_array}, " \
               f"address={self.address}, offset={self.offset}, "\
               f"size={self.size}, " \
               f"scope={self.scope}, data_type={self.data_type.name}, " \
               f"description={self.description}"

    def is_user_var(self) -> bool:
        return (self.id & 0x02) == 0x02