"""Pytest configuration for Karlsruhe SensorCity tests."""

from pathlib import Path
import sys

CONFIG_DIR = Path(__file__).parents[3] / "config"

sys.path.insert(0, str(CONFIG_DIR))
