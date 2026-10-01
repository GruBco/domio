#!/usr/bin/env python3
import runpy
import sys
from pathlib import Path

MODULE_NAME = 'scgi_server'

if __name__ == '__main__':
    sys.path.append(str(Path(__file__).parent.parent.resolve()))
    runpy.run_module("scgi_server", run_name='__main__')
