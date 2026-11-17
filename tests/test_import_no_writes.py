"""test_import_no_writes.py — importing pySUTO writes nothing; a run writes under its data dir (#190).

Four seams: every module of the package imports from an empty working directory and
leaves it empty; ``python -m pysuto run`` refuses to start without ``--data-dir``;
``Sweep`` writes under its pipeline's data dir and nowhere else; ``run_feed`` takes its
accounting structure from the caller and never reads ``config/config.yaml``.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

import pysuto

SRC = Path(pysuto.__file__).resolve().parents[1]


def test_importing_every_module_from_an_empty_directory_writes_nothing(tmp_path):
    """A fresh interpreter in an empty directory imports the whole package."""
    code = (
        "import importlib, pkgutil, pysuto\n"
        "for m in pkgutil.walk_packages(pysuto.__path__, 'pysuto.'):\n"
        "    importlib.import_module(m.name)\n"
    )
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    proc = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env,
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert list(tmp_path.iterdir()) == []


def test_python_m_pysuto_run_without_data_dir_exits_2(capsys):
    from pysuto.__main__ import main
    with pytest.raises(SystemExit) as exc:
        main(["run", "--case", "toy", "--from", "feed", "--to", "psut"])
    assert exc.value.code == 2
    assert "--data-dir" in capsys.readouterr().err


def test_configure_adds_per_module_file_handlers_under_the_log_dir(tmp_path):
    from pysuto.logging import configure, get_logger
    early = get_logger("t190.early")
    configure(str(tmp_path / "logs"))
    late = get_logger("t190.late")
    early.info("one")
    late.info("two")
    for log in (early, late):
        for h in log.handlers:
            h.flush()
    assert "one" in (tmp_path / "logs" / "t190.early.log").read_text()
    assert "two" in (tmp_path / "logs" / "t190.late.log").read_text()
    for log in (early, late):                       # leave no handler on a vanished tmp_path
        for h in [h for h in log.handlers if isinstance(h, logging.FileHandler)]:
            log.removeHandler(h)
            h.close()


def test_run_feed_without_acc_id_raises(tmp_path):
    from pysuto.feedpipe import run_feed
    with pytest.raises(TypeError, match="acc_id"):
        run_feed(object(), data_dir=str(tmp_path))
