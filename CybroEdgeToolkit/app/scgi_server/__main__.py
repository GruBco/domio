import sys

from lib.startup.runner import run_with_exit_code
from scgi_server import main


if __name__ == '__main__':
    sys.exit(run_with_exit_code(main))
