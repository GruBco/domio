import functools
import os
import re
from asyncio import AbstractEventLoop
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Tuple

from lib.general.conditional_logger import ConditionalLogger
from lib.general.misc import create_task_callback
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .alc_service.alc_parser import AlcParser
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .alc_service.var_info import VarInfo


class AlcService:
    CRC_FILENAME_REGEX = re.compile("^crc-(\\d+).alc")
    ENCODING = "latin-1"

    def __init__(self,
                 log: ConditionalLogger,
                 loop: AbstractEventLoop,
                 alc_dir: Path):
        self._log: ConditionalLogger = log
        self._loop: AbstractEventLoop = loop
        self._alc_dir: Path = alc_dir
        self._crc_to_alc: Dict[int, Dict[str, VarInfo]] = {}

    async def initialize_with_alc_files(self) -> None:
        async for crc, alc in self._read_alc_files():
            self._crc_to_alc[crc] = alc

    async def _read_alc_files(
        self
    ) -> AsyncGenerator[Tuple[int, Dict[str, VarInfo]], None]:
        if not self._alc_dir.exists():
            os.makedirs(self._alc_dir.resolve(), mode=0o755, exist_ok=False)
        else:
            for f in self._alc_dir.iterdir():
                if not f.is_file():
                    continue

                crc = self._filename_to_crc(f.name)
                if crc is None:
                    self._log.error(lambda:
                                    f"Invalid alc filename \"{f.name}\"")
                    continue

                alc = await self._load_alc(f)
                if alc is None:
                    continue

                yield crc, alc

    def set_alc_text(self, alc_text: str, crc: int) -> None:
        self._loop \
            .create_task(self._save_alc_text(alc_text, crc)) \
            .add_done_callback(create_task_callback(self._log))

        self[crc] = AlcParser.parse(alc_text)

    def __getitem__(self, crc: int) -> Dict[str, VarInfo]:
        return self._crc_to_alc[crc]

    def __setitem__(self, crc: int, alc: Dict[str, VarInfo]) -> None:
        self._log.info(f"Add alc with crc={crc}")
        self._crc_to_alc[crc] = alc

    async def _load_alc(self, path: Path) -> Optional[Dict[str, VarInfo]]:
        alc_text = await self._load_alc_text(path)
        if alc_text is None:
            return None
        return AlcParser.parse(alc_text)

    async def _save_alc_text(self, alc_text: str, crc: int) -> None:
        blocking_task = functools.partial(self._save_alc_text_blocking,
                                          alc_text,
                                          crc)
        return await self._loop.run_in_executor(None, blocking_task)

    async def load_alc_text_for_crc(self, crc: int) -> str:
        path = self._alc_dir.joinpath(self._crc_to_filename(crc))
        return await self._load_alc_text(path)

    async def _load_alc_text(self, path: Path) -> str:
        blocking_task = functools.partial(self._load_alc_text_blocking,
                                          path)
        return await self._loop.run_in_executor(None, blocking_task)

    def _save_alc_text_blocking(self, alc_text: str, crc: int) -> None:
        path = self._alc_dir.joinpath(self._crc_to_filename(crc))

        try:
            with path.open("w", encoding=self.ENCODING) as f:
                f.write(alc_text)
                f.flush()
        except OSError as e:
            self._log.debug(lambda: f"Can't save alc file \"{path}\"",
                            exc_info=e)
            self._log.debug(lambda: f"Can't save alc file \"{path}\": {e}")

    def _load_alc_text_blocking(self, alc_path: Path) -> str:
        try:
            with alc_path.open("r", encoding=self.ENCODING) as f:
                return f.read()
        except OSError as e:
            self._log.debug(lambda: f"Can't load alc file \"{alc_path}\"",
                            exc_info=e)
            self._log.error(lambda: f"Can't load alc file \"{alc_path}\": {e}")

    @classmethod
    def _crc_to_filename(cls, crc: int) -> str:
        return f"crc-{crc}.alc"

    @classmethod
    def _filename_to_crc(cls, filename: str) -> Optional[int]:
        match = cls.CRC_FILENAME_REGEX.match(filename)
        if match is None:
            return None

        crc_str = match.group(1)

        try:
            return int(crc_str)
        except ValueError:
            return None
