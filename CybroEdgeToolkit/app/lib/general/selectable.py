import os
import selectors


class Selectable:
    """Creates a dummy selectable resource for use to send custom read events
    to the selector.
    """
    def __init__(self):
        self._rfd, self._wfd = os.pipe()

    def __del__(self):
        try:
            os.close(self._rfd)
            os.close(self._wfd)
        except OSError:
            pass

    def fileno(self) -> int:
        """Gets file descriptor.

        :returns: file descriptor
        """
        return self._rfd

    def events(self) -> int:
        return selectors.EVENT_READ

    def trigger(self) -> None:
        """Trigger read event in the selector.
        """
        os.write(self._wfd, b'\0')

    def clear(self) -> None:
        """Clears triggered event.
        """
        os.read(self._rfd, 1)
