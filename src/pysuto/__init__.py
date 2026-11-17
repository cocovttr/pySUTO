"""pysuto
=====

Python-based Supply-Use Table Optimiser.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pysuto")
except PackageNotFoundError:  # source tree on sys.path, package not installed
    __version__ = "0+unknown"
