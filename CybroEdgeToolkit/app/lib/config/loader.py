from lib.config.ini_config_parser import IniConfigParser


class ConfigLoaderError(Exception):
    pass


class ConfigLoaderFileNotFoundError(Exception):
    pass

def read_config_from_file(config_file: str,
                          config_class,
                          defaults):
    """Reads config from init file into Config object.
    """
    icp = IniConfigParser()

    # read and parse the .ini file
    try:
        icp.parse(config_file)

    except FileNotFoundError as e:
        raise ConfigLoaderFileNotFoundError(
            f"Config missing: {config_file}"
        ) from e

    except Exception as e:
        raise ConfigLoaderError(
            f"Malformed config: {config_file}"
        ) from e

    # convert parsed data into the application-specific Config object
    # in a separate try/except block to catch situations where syntax is
    # valid but value errors occured or sections/keys are missing
    try:
        return config_class.load(icp, defaults)

    except Exception as e:
        raise ConfigLoaderError(
            f"Malformed config: {config_file}"
        ) from e
