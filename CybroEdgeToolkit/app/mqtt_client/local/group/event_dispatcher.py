import selectors
from asyncio import Task, AbstractEventLoop
from typing import Optional, Callable

from lib.general.conditional_logger import ConditionalLogger
from lib.general.selectable import Selectable

CallbackType = Optional[Callable[[], None]]

class GroupsEventDispatcher:
    def __init__(self,
                 log: ConditionalLogger,
                 loop: AbstractEventLoop):
        self._log = log
        self._loop = loop

        self._selector_changed: Selectable = Selectable()
        self._selector_publish: Selectable = Selectable()
        self._selector_socket: Selectable = Selectable()
        self._selector_stop: Selectable = Selectable()

        self._run: bool = False
        self._task: Optional[Task] = None

        self._changed_callback: CallbackType = None
        self._publish_callback: CallbackType = None
        self._socket_callback: CallbackType = None

    def trigger_changed(self):
        self._selector_changed.trigger()

    def trigger_publish(self):
        self._selector_publish.trigger()

    def trigger_socket(self):
        self._selector_socket.trigger()

    async def _task_run(self):
        """Handles changed, publish and socket events.
        """
        s = selectors.DefaultSelector()
        s.register(self._selector_changed, selectors.EVENT_READ)
        s.register(self._selector_publish, selectors.EVENT_READ)
        s.register(self._selector_socket, selectors.EVENT_READ)
        s.register(self._selector_stop, selectors.EVENT_READ)

        while self._run:
            events = await self._loop.run_in_executor(
                None,
                lambda: s.select()
            )
            for key, mask in events:
                if not (mask & selectors.EVENT_READ):
                    continue
                if key.fileobj == self._selector_changed:
                    if self._changed_callback:
                        self._changed_callback()
                    self._selector_changed.clear()
                elif key.fileobj == self._selector_publish:
                    if self._publish_callback:
                        self._publish_callback()
                    self._selector_publish.clear()
                elif key.fileobj == self._selector_socket:
                    if self._socket_callback:
                        self._socket_callback()
                    self._selector_socket.clear()
                elif key.fileobj == self._selector_stop:
                    self._selector_stop.clear()
                    break
                else:
                    self._log.debug(f"Unknown event {key.fileobj}")

        s.unregister(self._selector_changed)
        s.unregister(self._selector_publish)
        s.unregister(self._selector_socket)
        s.unregister(self._selector_stop)

    def start(self,
              changed_callback: CallbackType,
              publish_callback: CallbackType,
              socket_callback: CallbackType):
        self._changed_callback = changed_callback
        self._publish_callback = publish_callback
        self._socket_callback = socket_callback

        self._run = True
        self._task = self._loop.create_task(self._task_run())

    def stop(self):
        self._run = False
        self._selector_stop.trigger()

        self._changed_callback = None
        self._publish_callback = None
        self._socket_callback = None

        if self._task is not None:
            self._task.cancel()
            self._task = None
