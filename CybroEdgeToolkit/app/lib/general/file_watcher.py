import os
import sys
from pathlib import Path
from typing import Callable, Optional
from threading import Timer

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from lib.general.conditional_logger import ConditionalLogger


class FileWatcherError(Exception):
    pass


class FileWatcher:
    """Watches specified file for changes.

    On each change emits timestamp and file path as a tuple.
    """

    class EventHandler(FileSystemEventHandler):
        def __init__(self,
                     monitored_file: Path,
                     callback: Callable[[], None]):
            super().__init__()

            self._monitored_file = monitored_file
            self._callback = callback

        def on_any_event(self, event: FileSystemEvent) -> None:
            if event.is_directory:
                return

            src_path = Path(event.src_path)

            dest = getattr(event, "dest_path", None)
            dest_path = Path(dest) if dest else None

            # React only if the monitored file is either the source
            # or destination of the filesystem event.
            if src_path.name == self._monitored_file.name:
                self._callback()

            elif dest_path is not None and dest_path.name == self._monitored_file.name:
                self._callback()


    EVENT_DEBOUNCE_TIMER = 0.1   # time [s] after which filesystem events are processed

    def __init__(self, 
                 monitored_file: Path, 
                 callback: Callable[[], None]):
        self._monitored_file = monitored_file
        self._callback = callback
        self._last_modified = os.stat(monitored_file).st_mtime
        
        self._observer: Optional[Observer] = None
        self._check_timer: Optional[Timer] = None
        self._running = False

    def start(self) -> None:
        if self._running:
            raise FileWatcherError("Can't start cause it's already running")

        self._running = True

        self._observer = Observer()

        self._observer.schedule(
            self.EventHandler(
                self._monitored_file,
                self.reload_timer
            ),
            self._monitored_file.parent.as_posix(),
            recursive=False
        )

        self._observer.start()

    def stop(self) -> None:
        if not self._running:
            raise FileWatcherError("Can't stop cause it's not running")

        self._running = False

        if self._check_timer is not None:
            self._check_timer.cancel()
            self._check_timer = None

        self._observer.stop()
        self._observer = None

    def reload_timer(self) -> None:
        """ Reload the debounce timer for the monitored file. """

        if self._check_timer is not None:
            self._check_timer.cancel()

        self._check_timer = Timer(self.EVENT_DEBOUNCE_TIMER, self.update_subject_with_file)

        self._check_timer.start()

    def update_subject_with_file(self) -> None:
        """ Check the file timestamp after events settle. """

        self._check_timer = None

        try:
            new_time = os.stat(self._monitored_file).st_mtime

        except FileNotFoundError:
            # The file is still missing after debounce period. 
            # Restart so the config loader can report the missing config.
            self._callback()
            return

        if new_time != self._last_modified:
            self._last_modified = new_time
            self._callback()

    @staticmethod
    def restart(log: ConditionalLogger) -> None:
        log.info(sys.argv[0] + " " + sys.executable)
        args = sys.argv[:]

        log.info("Re-spawning %s" % " ".join(args))

        args.insert(0, sys.executable)

        if sys.platform == "win32":
            args = ['"%s"' % arg for arg in args]

        os.chdir(os.getcwd())
        os.execv(sys.executable, args)
