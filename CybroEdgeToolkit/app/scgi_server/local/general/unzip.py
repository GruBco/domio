import functools
import tempfile
import zipfile
from asyncio import get_running_loop

from scgi_server.local.general.errors import UnzipError


async def unzip(data: bytes) -> bytes:
    """Take zipped bytes and return unzipped bytes.

    Internally it uses python's `zipfile` module which creates temporary file.
    """

    blocking_task = functools.partial(_blocking_unzip, data)
    return await get_running_loop().run_in_executor(None,
                                                    blocking_task)


def _blocking_unzip(data: bytes) -> bytes:
    path = _make_temp_file()
    _save_to_file(path, data)
    return _read_from_file_and_unzip(path)


def _make_temp_file() -> str:
    try:
        (file_descriptor, path) = tempfile.mkstemp()
        return path
    except (OSError, FileExistsError) as e:
        raise UnzipError() from e


def _save_to_file(path: str, data: bytes) -> None:
    try:
        with open(path, "wb") as zipped_file:
            zipped_file.write(data)
            zipped_file.flush()
    except OSError as e:
        raise UnzipError() from e


def _read_from_file_and_unzip(path: str) -> bytes:
    try:
        with zipfile.ZipFile(path) as zipped_file:
            files = zipped_file.namelist()
            file = files[0]
            return zipped_file.read(file)
    except (FileExistsError, RuntimeError, IndexError) as e:
        raise UnzipError() from e
