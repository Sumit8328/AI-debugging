import os
import sys

# Ensure swarm-debugger is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
swarm_debugger_dir = os.path.join(root_dir, "swarm-debugger")
if swarm_debugger_dir not in sys.path:
    sys.path.insert(0, swarm_debugger_dir)

from backend.main import app, settings

__all__ = ["app", "settings"]
