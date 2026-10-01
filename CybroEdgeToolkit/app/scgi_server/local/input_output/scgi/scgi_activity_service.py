from datetime import datetime, timedelta


class ScgiActivityService:
    def __init__(self):
        self._server_start_datetime: datetime = datetime.now()
        self._requests_received_count: int = 0
        self._responses_sent_count: int = 0

    @property
    def requests_received_count(self) -> int:
        return self._requests_received_count

    @property
    def responses_sent_count(self) -> int:
        return self._responses_sent_count

    @property
    def server_uptime(self) -> timedelta:
        return datetime.now() - self._server_start_datetime

    def report_request_received(self) -> None:
        self._requests_received_count += 1

    def report_response_sent(self) -> None:
        self._responses_sent_count += 1