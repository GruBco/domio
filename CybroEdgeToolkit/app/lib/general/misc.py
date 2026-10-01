import asyncio


def create_task_callback(log):
    """Creates callback which will log when the task was canceled. It is used
    when we schedule the task on the loop and want to know that it was
    canceled.

    Args:
        log: logger which will be used to report task cancellation

    Returns:
        Callback
    """
    def callback(future):
        try:
            return future.result()
        except asyncio.CancelledError:
            log.debug("Task cancelled")

    return callback
