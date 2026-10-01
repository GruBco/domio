import asyncio
import logging
import sys
from asyncio import AbstractEventLoop, Future
from datetime import timedelta
from typing import Tuple, Optional

from scgi_server.local.general.errors import ExchangerTimeoutError
from scgi_server.local.input_output.abus_stack.abus.abus_message \
    import AbusMessage


class AbusExchanger:
    """Handles request-response cycles."""

    def __init__(self,
                 loop: AbstractEventLoop,
                 sender: 'Router',
                 timeout: timedelta,
                 retry: int):
        self._communication_loop: AbstractEventLoop = loop
        self._sender: 'Router' = sender

        # Sequence of (request, future) tuples where the future will be
        # resolved with a future response or error.
        if sys.version_info < (3, 10):
            self._requests_queue = asyncio.Queue(loop=self._communication_loop)
        else:
            self._requests_queue = asyncio.Queue()

        # Holds the exchange tag of the most recently sent request. It has to
        # be remembered throughout the read cycle, so it can be compared with
        # response exchange tags.
        self._last_exchange_tag: Optional[Tuple[int, int, int]] = None

        # Pending response for the request which has just been pulled from
        # the queue and sent.
        self._current_pending_response: Optional[Future] = None

        self._timeout: timedelta = timeout
        self._retry: int = retry

        self._communication_loop.create_task(self._handle_requests_queue())

    async def _handle_requests_queue(self) -> None:
        try:
            while True:
                request: AbusMessage
                #future: Future
                (request, future) = await self._requests_queue.get()

                try:
                    response = await self._exchange_with_retry_and_timeout(
                        request
                    )
                    future.set_result(response)
                except ExchangerTimeoutError as e:
                    future.set_exception(e)
        except Exception as e:
            logging.getLogger().error(f'Error in abus exchanger: {e}')

    async def exchange_threadsafe(self,
                                  request: AbusMessage) -> Future:
        return await asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(
                self._exchange_on_communication_loop(request),
                self._communication_loop
            )
        )

    async def _exchange_on_communication_loop(self,
                                              request: AbusMessage
                                              ) -> Future:
        future_response = self._communication_loop.create_future()

        self._requests_queue.put_nowait((request, future_response))

        return await future_response

    async def _exchange_with_retry_and_timeout(self,
                                               request: AbusMessage
                                               ) -> AbusMessage:
        retry = self._retry

        while retry > 0:
            try:
                return await self._exchange(request)
            except asyncio.TimeoutError:
                retry -= 1
        raise ExchangerTimeoutError()

    async def _exchange(self, request: AbusMessage) -> AbusMessage:
        """Sends a request message and wait on a response message.

        :param request: The request message to be sent.
        :return: Received response message.
        """
        if self._current_pending_response is not None:
            raise Exception('Current pending response should not exist')

        self._current_pending_response = (
            self._communication_loop.create_future()
        )
        self._last_exchange_tag = self._extract_exchange_tag_from_request(
            request
        )

        self._sender.send(request)

        try:
            return await asyncio.wait_for(
                self._current_pending_response,
                self._timeout.total_seconds()
            )
        finally:
            self._current_pending_response = None
            self._last_exchange_tag = None

    def receive(self, abus_msg: AbusMessage) -> None:
        exchange_tag = self._extract_exchange_tag_from_response(abus_msg)
        exchange_tags_match = exchange_tag == self._last_exchange_tag

        if exchange_tags_match \
                and self._current_pending_response is not None \
                and not self._current_pending_response.done():
            self._current_pending_response.set_result(abus_msg)

            self._last_exchange_tag = None
            self._current_pending_response = None

    @staticmethod
    def _extract_exchange_tag_from_request(
        abus_request: AbusMessage
    ) -> Tuple[int, int, int]:
        return (abus_request.from_nad,
                abus_request.to_nad,
                abus_request.transaction_id)

    @staticmethod
    def _extract_exchange_tag_from_response(
        abus_response: AbusMessage
    ) -> Tuple[int, int, int]:
        return (abus_response.to_nad,
                abus_response.from_nad,
                abus_response.transaction_id)
