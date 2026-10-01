class UdpActivityService:
    def __init__(self):
        self._rx_count: int = 0
        self._tx_count: int = 0

    @property
    def rx_count(self) -> int:
        return self._rx_count

    @property
    def tx_count(self) -> int:
        return self._tx_count

    def report_rx(self) -> None:
        self._rx_count += 1

    def report_tx(self) -> None:
        self._tx_count += 1
