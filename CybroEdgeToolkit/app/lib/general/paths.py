from pathlib import Path

# dir which is used to resolve all other relative paths
APP_DIR = Path(__file__).parent.parent.parent

# path to the main configuration file
CONFIG_FILE = APP_DIR.joinpath(Path("config.ini")).resolve()

# path to the data logger configuration file
DATA_LOGGER_CONFIG_FILE = APP_DIR.joinpath(Path("data_logger.xml")).resolve()