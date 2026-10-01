import ctypes
import os
from typing import Dict

from lib.general.timerfd import TimerFd, CLOCK_MONOTONIC, TFD_NONBLOCK, \
    itimerspec

TIMER_FD = TimerFd()


class Timestamp:
    def __init__(self, sec: int, nsec: int) -> None:
        """Container for second and nanosecond pairs.

        :param sec: seconds to set, must be 0 or positive integer
        :param nsec: nanoseconds to set, must be 0 or positive integer
        """
        if sec < 0 or nsec < 0:
            raise ValueError("Value must be positive integer")

        self._sec = sec
        self._nsec = nsec

    def __repr__(self) -> str:
        return str({
            'sec': self._sec,
            'nsec': self._nsec
        })

    @property
    def sec(self) -> int:
        return self._sec

    @property
    def nsec(self) -> int:
        return self._nsec

    @staticmethod
    def from_ms(ms: int):
        """Creates timestamp from the value in milliseconds.

        :param ms: value in milliseconds
        :returns: timestamp
        """
        if not isinstance(ms, int) or ms < 0:
            raise ValueError("Value must be positive integer")

        sec: int = int(ms / 1000)
        nsec: int = ms * 1_000_000 - sec * 1_000_000_000

        return Timestamp(sec=sec, nsec=nsec)

    @staticmethod
    def zero():
        """Creates timestamp with seconds and nanoseconds set to 0.

        :returns: timestamp
        """
        return Timestamp(sec=0, nsec=0)


class Timer:
    def __init__(self):
        """Creates timer which uses timerfd for raising events.
        """
        self._fd = TIMER_FD.create(CLOCK_MONOTONIC, TFD_NONBLOCK)

    def __del__(self):
        os.close(self._fd)

    @staticmethod
    def _raise_error() -> None:
        """Raises error with description from errno.
        """
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))

    def _validate(self) -> None:
        """Checks if the timer has initialized properly.
        """
        if self._fd < 0:
            self._raise_error()

    def _set_with_spec(self, spec: itimerspec) -> None:
        """Sets timer with provided specifications.

        :param spec: timer specifications
        """
        if TIMER_FD.settime(self._fd, 0, spec, None) < 0:
            self._raise_error()

    def fileno(self) -> int:
        """Gets file descriptor.

        :returns: file descriptor
        """
        return self._fd

    def set(self, ts: Timestamp) -> None:
        """Sets timer to time specified by the timestamp value.

        :param ts: seconds and nanoseconds to set the timer to
        :raises OSError: on error produced by timerfd_settime
        """
        self._validate()

        spec = itimerspec()
        spec.it_interval.tv_sec = 0
        spec.it_interval.tv_nsec = 0
        spec.it_value.tv_sec = ts.sec
        spec.it_value.tv_nsec = ts.nsec

        self._set_with_spec(spec)

    def set_periodic(self, ts: Timestamp) -> None:
        """Sets periodic time to time specified by the timestamp value.

        :param ts: seconds and nanoseconds to set the periodic timer to
        :raises OSError: on error produced by timerfd_settime
        """
        self._validate()

        spec = itimerspec()
        spec.it_interval.tv_sec = ts.sec
        spec.it_interval.tv_nsec = ts.nsec
        spec.it_value.tv_sec = ts.sec
        spec.it_value.tv_nsec = ts.nsec

        self._set_with_spec(spec)

    def stop(self) -> None:
        """Sets timer to zero time.

        :raises OSError: on error produced by timerfd_settime
        """
        self.set(Timestamp.zero())

    def get(self) -> Dict[str, Timestamp]:
        """Returns values which are set to current timer.

        :returns: current timer values
        """
        spec = itimerspec()
        if TIMER_FD.gettime(self._fd, spec) < 0:
            self._raise_error()

        return {
            'interval': Timestamp(spec.it_interval.tv_sec,
                                  spec.it_interval.tv_nsec),
            'value': Timestamp(spec.it_value.tv_sec,
                               spec.it_value.tv_nsec)
        }

    def clear_event(self) -> None:
        """Clears event in order for timer to continue. Without doing this
        periodic timer will not trigger and oneshot timer will be called
        multiple times in succession.
        """
        os.read(self._fd, 8)
