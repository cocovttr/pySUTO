"""test_import_no_writes.py
========================
Importing pySUTO writes nothing; a run writes under its data dir (#190).

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
        "import sys\n"
        "assert 'pysuto._step' in sys.modules\n"
    )
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    proc = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env,
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert list(tmp_path.iterdir()) == []


def test_step_child_starts_its_run_log_under_the_data_dir(tmp_path, monkeypatch):
    """The child of a pipeline step (#186) logs the #190 way: ``<data_dir>/logs``."""
    import json
    from dataclasses import asdict
    from pysuto import _step
    from pysuto import logging as plog
    seen = []
    monkeypatch.setattr(plog, "start_run_log", lambda d, name: seen.append((d, name)))
    monkeypatch.setattr(_step, "run_spec", lambda spec: "imp_x")
    spec = _step.StepSpec(step="imp", case="toy", label="l", upstream=None,
                          data_dir=str(tmp_path / "d"), config=None,
                          run_id_file=str(tmp_path / "rid"))
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(asdict(spec)))
    assert _step.main([str(path)]) == 0
    assert seen == [(str(tmp_path / "d"), "step_imp")]


def test_python_m_pysuto_run_without_data_dir_exits_2(capsys):
    from pysuto.__main__ import main
    with pytest.raises(SystemExit) as exc:
        main(["run", "--case", "toy", "--from", "feed", "--to", "psut"])
    assert exc.value.code == 2
    assert "--data-dir" in capsys.readouterr().err


@pytest.fixture
def fresh_log_state(monkeypatch):
    """Reset the module's log-dir state; close every file handler the test opened."""
    from pysuto import logging as plog
    monkeypatch.setattr(plog, "_LOG_DIR", None)
    created = []
    root_before = list(logging.getLogger().handlers)
    yield created
    for name in created:
        log = logging.getLogger(name)
        for h in [h for h in log.handlers if isinstance(h, logging.FileHandler)]:
            log.removeHandler(h)
            h.close()
    root = logging.getLogger()
    for h in [h for h in root.handlers if h not in root_before]:
        root.removeHandler(h)
        h.close()


def _flush(*logs):
    for log in logs:
        for h in log.handlers:
            h.flush()


def test_configure_file_logs_adds_per_module_handlers_under_the_log_dir(
        tmp_path, fresh_log_state):
    from pysuto.logging import configure_file_logs, get_logger
    fresh_log_state.extend(["t190.early", "t190.late"])
    early = get_logger("t190.early")
    configure_file_logs(str(tmp_path / "logs"))
    late = get_logger("t190.late")
    early.info("one")
    late.info("two")
    _flush(early, late)
    assert "one" in (tmp_path / "logs" / "t190.early.log").read_text()
    assert "two" in (tmp_path / "logs" / "t190.late.log").read_text()


def test_configure_file_logs_with_another_dir_moves_the_loggers(tmp_path, fresh_log_state):
    from pysuto.logging import configure_file_logs, get_logger
    fresh_log_state.append("t190.move")
    log = get_logger("t190.move")
    configure_file_logs(str(tmp_path / "a"))
    log.info("first")
    configure_file_logs(str(tmp_path / "b"))
    log.info("second")
    _flush(log)
    files = [h for h in log.handlers if isinstance(h, logging.FileHandler)]
    assert len(files) == 1
    assert "second" in (tmp_path / "b" / "t190.move.log").read_text()
    a = (tmp_path / "a" / "t190.move.log").read_text()
    assert "first" in a and "second" not in a


def test_start_run_log_makes_the_run_file_and_the_module_files(tmp_path, fresh_log_state):
    from pysuto.logging import get_logger, start_run_log
    fresh_log_state.append("t190.mod")
    log = get_logger("t190.mod")
    log_dir = start_run_log(str(tmp_path), "t190x")
    log.info("hello")
    _flush(log, logging.getLogger())
    assert log_dir == str(tmp_path / "logs")
    runs = list((tmp_path / "logs").glob("t190x_*.log"))
    assert len(runs) == 1
    assert "hello" in runs[0].read_text()
    assert "hello" in (tmp_path / "logs" / "t190.mod.log").read_text()


def test_run_feed_without_acc_id_raises(tmp_path):
    from pysuto.feedpipe import run_feed
    with pytest.raises(TypeError, match="acc_id"):
        run_feed(object(), data_dir=str(tmp_path))
