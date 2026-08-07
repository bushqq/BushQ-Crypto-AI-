#!/usr/bin/env python3
"""BushQ Crypto AI - Windows desktop app entry."""

import os
import shutil
import sys


if getattr(sys, "frozen", False):
    project_root = os.path.dirname(sys.executable)
else:
    project_root = os.path.dirname(os.path.abspath(__file__))

os.chdir(project_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

config_path = os.path.join(project_root, "config", "config.yaml")
example_path = os.path.join(project_root, "config", "config.example.yaml")
if getattr(sys, "frozen", False) and not os.path.exists(config_path) and os.path.exists(example_path):
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    shutil.copyfile(example_path, config_path)

from gui_app import main


if __name__ == "__main__":
    main()
