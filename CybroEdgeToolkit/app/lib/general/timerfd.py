import ctypes
from typing import Optional

# A settable system-wide real-time clock.
CLOCK_REALTIME = 0
# A nonsettable monotonically increasing clock that measures time from some
# unspecified point in the past that does not change after system startup.
CLOCK_MONOTONIC = 1
# Like CLOCK_MONOTONIC, this is monotonically increasing clock. However,
# whereas the CLOCK_MONOTONIC clock does not measure the time while system is
# suspended, the CLOCK_BOOTTIME clock does include the time during which the
# system is suspended. This is useful for applications that need to be
# suspend-aware. CLOCK_REALTIME is not suitable fo such application, since that
# clock is affected by discontinuous changes to the system clock.
CLOCK_BOOTTIME = 7
# This clock is like CLOCK_REALTIME, but will wake the system is it is
# suspended. The caller must have the CAP_WAKE_ALARM capability in order to set
# a timer against this clock.
CLOCK_REALTIME_ALARM = 8
# THis clock is like CLOCK_BOOTTIME, but will wake the system if it is
# suspended. The caller must have the CAP_WAKE_ALARM capability in order to set
# a timer against this clock.
CLOCK_BOOTTIME_ALARM = 9

# Set the close-on-exec (FD_CLOEXEC) flag on the new file descriptor. See the
# description of the O_CLOEXEC flag in open for reasons why this may be
# useful.
TFD_CLOEXEC = 0o02000000
# Set to O_NONBLOCK file status flag on the open file description (see open)
# referred by the new file descriptor. Using this flag saves extra calls to
# fcntl to achieve the same result.
TFD_NONBLOCK = 0o00004000

# Interpret new_value.it_value AS an absolute value on the timer's clock. The
# timer will expire when the value of the timer's clock reaches the value
# specified in new_value.it_value.
TFD_TIMER_ABSTIME = 1
# If this flags is specified along with TFD_TIMER_ABSTIME and the clock for
# this is CLOCK_REALTIME or CLOCK_REALTIME_ALARM, then mark this timer as
# cancelable if the real-time clock undergoes a discontinuous change. When
# such changes occur, a current of future read(2) from the file descriptor
# will fail with the error ECANCELED.
TFD_TIMER_CANCEL_ON_SET = 2

# integer time
c_time_t = ctypes.c_long


class timespec(ctypes.Structure):
    """Time in seconds and nanoseconds.
    """
    _fields_ = [
        # Seconds
        ("tv_sec", c_time_t),
        # Nanoseconds [0, 999'999'999]
        ("tv_nsec", c_time_t)
    ]


class itimerspec(ctypes.Structure):
    """Interval for a time with nanosecond precision.
    """
    _fields_ = [
        # Interval for periodic timer
        ("it_interval", timespec),
        # Initial expiration
        ("it_value", timespec),
    ]


class TimerFd:
    def __init__(self):
        libc = ctypes.CDLL("libc.so.6", use_errno=True)

        self._timerfd_create = libc.timerfd_create
        self._timerfd_create.argtypes = [ctypes.c_int, ctypes.c_int]
        self._timerfd_create.restype = ctypes.c_int

        self._timerfd_settime = libc.timerfd_settime
        self._timerfd_settime.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(itimerspec),
            ctypes.POINTER(itimerspec)
        ]
        self._timerfd_settime.restype = ctypes.c_int

        self._timerfd_gettime = libc.timerfd_gettime
        self._timerfd_gettime.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(itimerspec)
        ]
        self._timerfd_gettime.restype = ctypes.c_int

    def create(self, clock_id: int, flags: int) -> int:
        """Creates timerfd.

        :param clock_id: Clock that is used to mark the progress of the timer.
        :param flags: TFD_CLOEXEC or TFD_NONBLOCK, can be bitwise or-ed
        :return: file descriptor or -1 on error and sets errno
        """
        return self._timerfd_create(clock_id, flags)

    def settime(self,
                fd: int,
                flags: int,
                new_value: itimerspec,
                old_value: Optional[itimerspec]) -> int:
        """Starts or stops the timer referred to by the file descriptor fd.

        :param fd: file descriptor
        :param flags: TFD_TIMER_ABSTIME or TFD_TIMER_CANCEL_ON_SET, can be
        bitwise or-ed
        :param new_value: interval and initial start time
        :param old_value: returns interval and initial start time on the time
        of the call
        :return: 0 on success, -1 on error and sets errno
        """
        return self._timerfd_settime(fd, flags, new_value, old_value)

    def gettime(self, fd: int, curr_value: itimerspec) -> int:
        """Gets current setting of the timer referred by the file descriptor
        fd.

        :param fd: file descriptor
        :param curr_value: interval and initial start time
        :return: 0 on success, -1 on error and sets errno
        """
        return self._timerfd_gettime(fd, curr_value)
