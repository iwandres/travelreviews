"""
PunFiction Consolidated Admin & API Server Entrypoint.
Delegates directly to unified_server so local and production servers stay 100% aligned.
"""
import os
import sys

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
if DIR_PATH not in sys.path:
    sys.path.insert(0, DIR_PATH)

try:
    from unified_server import *  # noqa: F401,F403
except ImportError:
    from backend.unified_server import *  # noqa: F401,F403


if __name__ == '__main__':
    run_server()
