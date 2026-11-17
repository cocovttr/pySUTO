"""test_packaging.py
===================

The installed package reports a version and exposes the ``pysuto`` command.
"""
from __future__ import annotations

import pytest

import pysuto
from pysuto.__main__ import main


def test_version_is_non_empty_string():
    assert isinstance(pysuto.__version__, str) and pysuto.__version__


def test_main_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "usage" in capsys.readouterr().out.lower()
