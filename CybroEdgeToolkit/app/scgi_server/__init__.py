#!/usr/bin/env python

import logging
import sys
import os
from asyncio import AbstractEventLoop

from lib.config.loader import (
    ConfigLoaderError,
    ConfigLoaderFileNotFoundError,
    read_config_from_file,
)
from lib.general.paths import CONFIG_FILE
from lib.startup.init_logging import init_logging
from lib.startup.runner import run_with_exit_code
from scgi_server.local.config.config import Config
from scgi_server.local.config.config_defaults import DEFAULT_CONFIG
from scgi_server.local.container import Container
from scgi_server.local.errors import ScgiServerError

async def main(
    main_loop: AbstractEventLoop,
    comm_loop: AbstractEventLoop
) -> None:
    try:
        config = read_config_from_file(CONFIG_FILE, Config, DEFAULT_CONFIG)
        init_logging(config.debuglog_config,
                     config.locations_config.log_dir,
                     "scgi")

        container = Container(
            config,
            main_loop,
            comm_loop,
            sys.argv[0]
        )

        await container.scgi_server_bootstrap.run()

    except ConfigLoaderFileNotFoundError as e:
        init_logging(
            DEFAULT_CONFIG.debuglog_config,
            DEFAULT_CONFIG.locations_config.log_dir,
            "scgi"
        )
        logging.critical(f"{e} (exit code 4)")
        logging.shutdown()
        os._exit(4)

    except ConfigLoaderError as e:
        init_logging(
            DEFAULT_CONFIG.debuglog_config,
            DEFAULT_CONFIG.locations_config.log_dir,
            "scgi"
        )
        logging.critical(f"{e} (exit code 5)")
        logging.shutdown()
        os._exit(5)

    except ScgiServerError as e:
        logging.critical(e)
        raise

    except Exception as e:
        logging.critical(e, exc_info=e)
        raise


if __name__ == "__main__":
    sys.exit(run_with_exit_code(main))
