#!/usr/bin/env python

import logging
import sys
import os
from asyncio import AbstractEventLoop

from lib.config.loader import (
        ConfigLoaderError,
        ConfigLoaderFileNotFoundError,
        read_config_from_file
)
from lib.general.paths import CONFIG_FILE
from lib.startup.init_logging import init_logging
from lib.startup.runner import run
from mqtt_client.local.config.config import Config
from mqtt_client.local.config.config_defaults import DEFAULT_CONFIG
from mqtt_client.local.container import Container


async def main(main_loop: AbstractEventLoop,
               comm_loop: AbstractEventLoop) -> None:
    try:
        config: Config = read_config_from_file(CONFIG_FILE,
                                               Config,
                                               DEFAULT_CONFIG)
        init_logging(config.debuglog_config,
                     config.locations_config.log_dir,
                     "mqtt_client")

        container = Container(config, main_loop, comm_loop, sys.argv[0])

        await container.bootstrap.run()

    except ConfigLoaderFileNotFoundError as e:
        init_logging(
            DEFAULT_CONFIG.debuglog_config,
            DEFAULT_CONFIG.locations_config.log_dir,
            "mqtt"
        )
        logging.critical(f"{e} (exit code 4)")
        logging.shutdown()
        os._exit(4)

    except ConfigLoaderError as e:
        init_logging(
            DEFAULT_CONFIG.debuglog_config,
            DEFAULT_CONFIG.locations_config.log_dir,
            "mqtt"
        )
        logging.critical(f"{e} (exit code 5)")
        logging.shutdown()
        os._exit(5)
    
    except ConnectionError:
        logging.shutdown()
        os._exit(1)

    except Exception as e:
        logging.critical(e, exc_info=e)
        raise

if __name__ == '__main__':
    sys.exit(run(main))
