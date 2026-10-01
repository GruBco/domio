import sys

from lib.startup.runner import run
from mqtt_client import main

if __name__ == '__main__':
    sys.exit(run(main))
