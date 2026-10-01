import asyncio
from asyncio import AbstractEventLoop
from typing import Callable, Coroutine

from scgi_server.local.config.eth_config import SocketsType
from lib.general.conditional_logger import ConditionalLogger
from lib.services.alias_service import AliasService
from scgi_server.local.input_output.abus_stack.abus.abus_message import \
    AbusMessage
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .alc_service.alc_service import AlcService
from scgi_server.local.services.rw_service.subservices.plc_comm_service \
    .plc_comm_service import PlcCommService
from scgi_server.local.services.socket_service.socket_message import \
    SocketMessage


class SocketService:
    def __init__(self,
                 log: ConditionalLogger,
                 loop: AbstractEventLoop,
                 alc_service: AlcService,
                 plc_comm_service: PlcCommService,
                 alias_service: AliasService,
                 send_client_message_handler: Callable[
                     [bytes], Coroutine[None, None, None]
                 ],
                 sockets: SocketsType):
        self._log = log
        self._loop = loop
        self._alc_service = alc_service
        self._plc_comm_service = plc_comm_service
        self._alias_service: AliasService = alias_service
        self._send_client_message_handler = send_client_message_handler
        self._sockets: SocketsType = sockets

    async def _propagate_socket_message(self, abus_msg: AbusMessage):
        """Serializes an ABUS socket message to XML and sends it to clients via
        send_client_message_handler call.

        :param abus_msg: ABUS message
        """
        crc = await self._loop.create_task(
            self._plc_comm_service.get_crc(abus_msg.from_nad)
        )

        sm = SocketMessage.create(
            abus_message=abus_msg,
            alc_var_info=self._alc_service[crc],
            socket_config=self._sockets
        )

        xml = sm.to_xml(self._alias_service)

        # noinspection PyUnresolvedReferences
        await self._send_client_message_handler(xml)

    def receive(self, abus_msg: AbusMessage) -> None:
        """Process a received ABUS socket message and send it to clients.

        :param abus_msg: ABUS message
        """
        self._log.debug(f"Received socket message: {abus_msg}")
        asyncio.run_coroutine_threadsafe(
            self._propagate_socket_message(abus_msg), self._loop
        )
