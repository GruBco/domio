#!/usr/bin/env python3
import runpy
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.resolve()))

if __name__ == '__main__':
    runpy.run_module('mqtt_client', run_name='__main__')
