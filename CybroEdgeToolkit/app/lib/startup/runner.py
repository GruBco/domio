import os
import signal
import asyncio
import errno
import traceback
from asyncio import AbstractEventLoop
from threading import Thread
from typing import Callable, Coroutine, Tuple, Any, Dict, Optional

from lib.config.loader import ConfigLoaderFileNotFoundError, ConfigLoaderError
from lib.general import exit_codes
from lib.startup.exceptions import UDPPortError, TCPPortError, MissingError

DEBUG = False

MainCoroutineType = Callable[
    [AbstractEventLoop, AbstractEventLoop], Coroutine[None, None, None]
]

def _handle_sigterm(signum, frame):
    os._exit(exit_codes.TERMINATED_BY_SIGTERM)

def _process_exception(exception: BaseException) -> int:
    """Translates exception by type to exit code.

    :param exception: The exception to translate.
    :return: The exit code.
    """
    if isinstance(exception, FileNotFoundError) or \
        isinstance(exception, ConfigLoaderFileNotFoundError):
        return exit_codes.CANT_OPEN_CONFIG_INI
    elif isinstance(exception, ConfigLoaderError):
        return exit_codes.CONFIG_INI_PARSING_ERROR
    elif isinstance(exception, UDPPortError):
        return exit_codes.CANT_OPEN_UDP_PORT
    elif isinstance(exception, TCPPortError):
        return exit_codes.CANT_OPEN_SCGI_PORT
    elif isinstance(exception, OSError) and \
        exception.errno == errno.EADDRINUSE:
        return exit_codes.UNSPECIFIED_ERROR
    elif isinstance(exception, KeyboardInterrupt):
        return exit_codes.TERMINATED_BY_CTRLC
    else:
        return exit_codes.UNSPECIFIED_ERROR


def _exception_handler(
    context: Dict[str, Any],
    kill_run: Callable,
    exit_code: asyncio.Future,
    output: Optional[Callable[[Exception], None]] = None
) -> None:
    """Handles exceptions thrown by running loop.

    :param context: The context is set by the set_exception_handler method
    from which to extract a thrown exception object.
    :param kill_run: Function used to kill running loop.
    :param exit_code: Future for setting program exit code.
    """
    exception = context.get('exception', MissingError)
    if output is not None:
        output(exception)

    try:
        exit_code.set_result(_process_exception(exception))
    except asyncio.exceptions.InvalidStateError as ex:
        if output is not None:
            output(ex)

    kill_run()


def run_with_exit_code(main_coro: MainCoroutineType) -> int:
    """Create a communication loop which will handle abus-related data flow
    throughout the application.
    Everything else will be done on the main thread (the one this code is
    currently running on).

    :param main_coro: Coroutine to run.
    """

    signal.signal(signal.SIGTERM, _handle_sigterm)

    communication_loop, kill_communication_loop = (
        create_thread_loop("CommunicationThread")
    )

    running_loop = asyncio.new_event_loop()
    completed = running_loop.create_future()
    exit_code = running_loop.create_future()

    try:
        def kill_run_loop():
            kill_communication_loop()

            if running_loop.is_running():
                if not completed.done():
                    completed.set_result(None)

                pending = asyncio.all_tasks(running_loop)
                for t in pending:
                    if not t.done() and not t.cancelled():
                        t.cancel()

                if pending:
                    running_loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )

        running_loop.set_exception_handler(
            lambda _, context: _exception_handler(
                context, kill_run_loop, exit_code
            )
        )

        running_loop.create_task(main_coro(running_loop, communication_loop))
        try:
            running_loop.run_until_complete(completed)
        except asyncio.CancelledError:
            pass

        for task in asyncio.all_tasks(running_loop):
            if not task.done():
                running_loop.run_until_complete(task)

        running_loop.close()
        running_loop.set_exception_handler(None)
        if exit_code.done():
            return exit_code.result()
        else:
            if DEBUG:
                print("Exit code not set")
            return exit_codes.UNSPECIFIED_ERROR
    except KeyboardInterrupt:
        if DEBUG:
            print("KeyboardInterrupt")
        os._exit(exit_codes.TERMINATED_BY_CTRLC)
    except Exception as ex:
        if DEBUG:
            print("Exception raised: ", ex)
        running_loop.set_exception_handler(None)
        if exit_code.done():
            return exit_code.result()
        else:
            return _process_exception(ex)


def run(main_coro: MainCoroutineType) -> int:
    signal.signal(signal.SIGTERM, _handle_sigterm)
    communication_loop, kill_communication_loop = (
        create_thread_loop("CommunicationThread")
    )

    running_loop = asyncio.new_event_loop()
    complete = running_loop.create_future()
    exit_code = running_loop.create_future()

    def kill_run_loop():
        complete.set_result(None)
        kill_communication_loop()

    def output(ex: Exception) -> None:
        cex = ex
        while cex is not None:
            if cex.__traceback__:
                traceback.print_tb(cex.__traceback__)

            cex = cex.__cause__

    try:
        running_loop.create_task(main_coro(running_loop, communication_loop))
        running_loop.set_exception_handler(
            lambda _, context: _exception_handler(
                context,
                kill_run_loop,
                exit_code,
                output
            )
        )
        running_loop.run_until_complete(complete)
        running_loop.set_exception_handler(None)
        running_loop.close()
    except KeyboardInterrupt:
        if DEBUG:
            print("KeyboardInterrupt")
        os._exit(exit_codes.TERMINATED_BY_CTRLC)
    except BaseException as e:
        print(e)
        return exit_codes.UNSPECIFIED_ERROR

    return exit_code.result()


def run_simple(main_coro: Callable[
    [AbstractEventLoop], Coroutine[None, None, None]
]) -> None:
    try:
        running_loop = asyncio.new_event_loop()
        running_loop.create_task(main_coro(running_loop))
        running_loop.run_forever()
    except BaseException as e:
        print(e)


def create_thread_loop(name: str) -> Tuple[AbstractEventLoop, Callable]:
    """Create a new thread and then start a new asyncio event loop inside it.

    Args:
        name: Name of the new thread.

    Returns:
        Tuple containing asyncio loop and `kill` function which will stop the
        loop and the associated thread.
    """

    loop = asyncio.new_event_loop()
    kill_switch = loop.create_future()

    # this function will be called in the newly created thread
    def start_loop(loop_to_start):
        asyncio.set_event_loop(loop_to_start)
        loop_to_start.run_until_complete(kill_switch)

    t = Thread(target=start_loop, args=(loop,), name=name)
    t.start()

    def kill():
        if not loop.is_closed():
            loop.call_soon_threadsafe(lambda: kill_switch.set_result(True))

    return loop, kill
