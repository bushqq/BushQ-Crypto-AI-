#!/usr/bin/env python3
"""BushQ Crypto AI - Windows desktop app entry."""

import os
import sys


if getattr(sys, "frozen", False):
    project_root = os.path.dirname(sys.executable)
else:
    project_root = os.path.dirname(os.path.abspath(__file__))

os.chdir(project_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui_app import main


if __name__ == "__main__":
    main()
