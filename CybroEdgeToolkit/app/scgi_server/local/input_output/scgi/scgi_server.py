from typing import Optional, List

from lib.general.conditional_logger import ConditionalLogger
from lib.input_output.http.messages import \
    HttpRequestMessage, HttpResponseMessage
from lib.input_output.scgi.r_response import RResponse
from lib.input_output.scgi.rw_responses_xml_serializer import \
    RRResponsesXmlSerializer
from lib.services.alias_service import AliasService, AliasError
from scgi_server.local.input_output.scgi.operation import OperationUtil
from scgi_server.local.input_output.scgi.scgi_activity_service import \
    ScgiActivityService
from scgi_server.local.services.rw_service.errors import InvalidTagNameError
from scgi_server.local.services.rw_service.rw_service import RWService
from scgi_server.local.services.rw_service.scgi_communication.rw_request \
    import RWRequest


class ScgiServer:
    def __init__(self,
                 log: ConditionalLogger,
                 rw_service: RWService,
                 scgi_activity_service: ScgiActivityService,
                 alias_service: AliasService,
                 reply_with_descriptions: bool,
                 access_token: Optional[str]):
        self._log: ConditionalLogger = log
        self._rw_service: RWService = rw_service
        self._scgi_activity_service: ScgiActivityService = (
            scgi_activity_service
        )
        self._reply_with_descriptions: bool = reply_with_descriptions
        self._access_token: Optional[str] = access_token
        self._alias_service: AliasService = alias_service
        self._controller_not_found_msg = str(HttpResponseMessage.not_found(
            body="Controller doesn't exist"
        ))

    async def on_data(self, data: bytes) -> bytes:
        self._scgi_activity_service.report_request_received()

        response_str = await self._on_data(data)
        response = response_str.encode()

        self._scgi_activity_service.report_response_sent()

        return response

    @staticmethod
    def _create_device_not_found(name: str) -> RResponse:
        return RResponse.create(
            name=name,
            tag_name='',
            valid=False,
            code=RResponse.Code.DEVICE_NOT_FOUND
        )

    async def _on_data(self, data: bytes) -> str:
        try:
            try:
                msg = HttpRequestMessage.parse_request(data.decode())
                if msg.uri == '/favicon.ico':
                    return str(HttpResponseMessage.not_found())

                if self._access_token is not None:
                    auth = msg.headers.get('Authorization', ' ').split(" ")[1]
                    if auth != self._access_token:
                        self._log.error("Unauthorized: Access token mismatch")
                        return str(HttpResponseMessage.unauthorized())

                _, query_string = msg.uri.split("?")

                (
                    read_operations,
                    write_operations,
                    error_operations
                ) = OperationUtil.bytes_to_operations(query_string,
                                                      self._alias_service)
            except Exception as e:
                self._log.debug("Bad request", exc_info=e)
                self._log.error(f"Bad request: {e}")
                return str(HttpResponseMessage.bad_request())

            e_responses = [
                self._create_device_not_found(operation.key)
                for operation in error_operations
            ]

            r_requests: List[RWRequest] = []
            for op in read_operations:
                try:
                    r_requests.append(RWRequest.create(op.key, op.value))
                except InvalidTagNameError:
                    e_responses.append(self._create_device_not_found(op.key))

            w_requests: List[RWRequest] = []
            for op in write_operations:
                try:
                    w_requests.append(RWRequest.create(op.key, op.value))
                except InvalidTagNameError:
                    e_responses.append(self._create_device_not_found(op.key))

            try:
                responses = await self._rw_service.on_rw_requests(r_requests,
                                                                  w_requests)
            except ValueError as ex:
                self._log.debug("Bad request", exc_info=ex)
                self._log.error(f"Bad request: {ex}")
                return str(HttpResponseMessage.bad_request())

            xml = RRResponsesXmlSerializer.to_xml(
                responses + e_responses,
                [op.key for op in error_operations],
                self._reply_with_descriptions,
                self._alias_service
            )

            return str(HttpResponseMessage.ok(
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'text/xml',
                    'Content-Length': str(len(xml)),
                    'Connection': 'close'
                },
                body=xml
            ))
        except Exception as e:
            self._log.debug("Internal Server Error", exc_info=e)
            self._log.error(f"Internal Server Error: {e}")
            return str(HttpResponseMessage.internal_server_error())
