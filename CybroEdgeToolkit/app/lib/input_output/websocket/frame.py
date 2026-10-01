import struct
from dataclasses import dataclass
from enum import Enum
from os import urandom
from typing import Optional


class Opcode(Enum):
    CONTINUATION = 0
    TEXT = 1
    BINARY = 2
    CLOSE = 8
    PING = 9
    PONG = 10


@dataclass(frozen=True)
class WebSocketFrame:
    """WebSocket frame object representation of binary message data.
    """
    fin: bool
    opcode: Opcode
    rsv1: bool
    rsv2: bool
    rsv3: bool
    mask_key: Optional[bytes]
    payload_len: int
    payload: bytes
    status_code: Optional[int] = None

    @property
    def has_mask(self):
        return self.mask_key is not None

    def __str__(self):
        sc = f",status_code={self.status_code}" if self.status_code else ""
        mask_key = self.mask_key.hex(sep=' ') if self.has_mask else None
        return (f"fin={self.fin},"
                f"rsv1={self.rsv1},"
                f"rsv2={self.rsv2},"
                f"rsv3={self.rsv3},"
                f"opcode={self.opcode.name},"
                f"mask_key={mask_key},"
                f"payload_len={self.payload_len},"
                f"data={self.payload.hex(sep=' ')}"
                f"{sc}")

    def _frame_first_byte(self) -> bytes:
        return struct.pack(
            "B",
            (0x80 if self.fin else 0x00) |
            (0x40 if self.rsv1 else 0x00) |
            (0x20 if self.rsv2 else 0x00) |
            (0x10 if self.rsv3 else 0x00) |
            self.opcode.value
        )

    def _frame_second_byte(self) -> bytes:
        if self.payload_len <= 125:
            return struct.pack(
                "B",
                (self.payload_len & 0x7f) |
                (0x80 if self.mask_key is not None else 0x00)
            )
        elif self.payload_len <= 65536:
            return struct.pack(
                ">BH",
                0xFE if self.mask_key is not None else 0x7E,
                self.payload_len
            )
        else:
            return struct.pack(
                ">BQ",
                0xFF if self.mask_key is not None else 0x7F,
                self.payload_len
            )

    @staticmethod
    def gen_mask() -> bytes:
        """Randomly generates 4 byte mask key.
        """
        return urandom(4)

    @staticmethod
    def mask_data(masking_key: bytes, data: bytes) -> bytes:
        """Masks the given data with the given masking key.
        """
        return b''.join(
            (data[i] ^ masking_key[i % 4]).to_bytes(1, byteorder='little')
            for i in range(0, len(data))
        )

    def serialize(self) -> bytes:
        """Returns bytes representation of WebSocket frame.
        """
        msg: bytes = self._frame_first_byte() + self._frame_second_byte()

        if self.mask_key is not None:
            msg += (self.mask_key +
                    WebSocketFrame.mask_data(self.mask_key, self.payload))
        else:
            msg += self.payload

        return msg

    @classmethod
    def deserialize(cls, msg: bytes):
        """Creates a WebSocketFrame instance from a bytes message.
        """
        fin = (msg[0] & 0x80 != 0)
        rsv1 = (msg[0] & 0x40 != 0)
        rsv2 = (msg[0] & 0x20 != 0)
        rsv3 = (msg[0] & 0x10 != 0)
        opcode = Opcode(msg[0] & 0x0F)
        has_mask = (msg[1] & 0x80 != 0)

        payload_len = int(msg[1] & 0x7F)
        if payload_len == 0x7E:
            payload_len = struct.unpack(">H", msg[2:4])[0]
            mask_key = msg[4:8] if has_mask else None
            payload_idx = 8 if has_mask else 4
        elif payload_len == 0x7F:
            payload_len = struct.unpack(">Q", msg[2:10])[0]
            mask_key = msg[10:14] if has_mask else None
            payload_idx = 14 if has_mask else 10
        else:
            mask_key = msg[2:6] if has_mask else None
            payload_idx = 6 if has_mask else 2

        unmasked_payload = cls.mask_data(
            mask_key,
            msg[payload_idx:payload_idx + payload_len]
        ) if has_mask else msg[payload_idx:payload_idx + payload_len]

        status_code = struct.unpack(">H", unmasked_payload)[0] \
            if opcode == Opcode.CLOSE \
            else None

        return cls(
            fin=fin,
            opcode=opcode,
            rsv1=rsv1,
            rsv2=rsv2,
            rsv3=rsv3,
            mask_key=mask_key,
            payload_len=payload_len,
            payload=unmasked_payload,
            status_code=status_code
        )

    @classmethod
    def for_payload(cls, payload: bytes, client: bool = False):
        """Creates text frame for specified payload.
        """
        return cls(
            fin=True,
            opcode=Opcode.TEXT,
            rsv1=False,
            rsv2=False,
            rsv3=False,
            # server sent message must not use mask
            mask_key=WebSocketFrame.gen_mask() if client else None,
            payload_len=len(payload),
            payload=payload
        )

    @classmethod
    def close(cls, status_code: int, client: bool = False):
        return cls(
            fin=True,
            opcode=Opcode.CLOSE,
            rsv1=False,
            rsv2=False,
            rsv3=False,
            mask_key=WebSocketFrame.gen_mask() if client else None,
            payload_len=2,
            payload=struct.pack(">H", status_code),
            status_code=status_code
        )

    @classmethod
    def ping(cls, data: str, client: bool = False):
        payload = data.encode()
        return cls(
            fin=True,
            opcode=Opcode.PING,
            rsv1=False,
            rsv2=False,
            rsv3=False,
            mask_key=WebSocketFrame.gen_mask() if client else None,
            payload_len=len(payload),
            payload=payload
        )

    @classmethod
    def pong(cls, ping_payload: bytes, client: bool = False):
        """Creates pong response frame with ping payload.
        """
        return cls(
            fin=True,
            opcode=Opcode.PONG,
            rsv1=False,
            rsv2=False,
            rsv3=False,
            mask_key=WebSocketFrame.gen_mask() if client else None,
            payload_len=len(ping_payload),
            payload=ping_payload
        )
