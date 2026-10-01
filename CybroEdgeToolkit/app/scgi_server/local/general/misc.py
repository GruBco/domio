from typing import List, Union

from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .data_type import DataType


def split_at_index(sequence: List[Union[int, DataType]], index: int):
    """Split `sequence` into left and right part.

    Args:
        sequence (List[int])
        index: Place at which to make the split.

    Returns:
        Tuple with left and right part.
    """

    return sequence[:index], sequence[index:]


def chunk(sequence: bytes, size: int):
    """Break `sequence` into chunks which are at most `size` long.

    Returns:
        None

    Yields:
        Chunks in the order they are being made.
    """

    s = sequence
    while len(s) != 0:
        yield s[:size]
        s = s[size:]
