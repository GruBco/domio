class Ticker:
    def __init__(self, period: int):
        """Tracks the period passed between ticks. If for example we use
        seconds for ticks: set period to 10 and call tick each second by
        amount 1, timeout will occur after 10 seconds.

        :param period: The amount of time to be ticked.
        """
        self._period = period
        self._timeout = period

    def is_enabled(self) -> bool:
        """Checks if the ticker is enabled.

        :return: True if the ticker is enabled, False otherwise
        """
        return self._period > 0

    def is_expired(self) -> bool:
        """Checks if the ticker has expired.

        :return: True if the ticker is expired, False otherwise
        """
        return self._timeout <= 0

    def tick(self, amount: int = 1):
        """Ticks the ticker.

        :param amount: The amount of time to be ticked (defaults to 1).
        """
        self._timeout -= amount

    def reset(self) -> None:
        """Resets the ticker.
        """
        self._timeout = self._period
