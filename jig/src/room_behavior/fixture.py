"""Thin wrapper so the fixture generator has one import site."""

from __future__ import annotations

import importlib.util
import pathlib

from . import cells as cells_module


def _generator():
    path = cells_module.jig_root() / "fixtures" / "orders.py"
    spec = importlib.util.spec_from_file_location("_orders", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_fixture(destination: pathlib.Path) -> str:
    """Write the room-volume fixture; return the expected answer."""
    return _generator().write(destination)
