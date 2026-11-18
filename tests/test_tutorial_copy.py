"""test_tutorial_copy.py — ``python -m pysuto tutorial [DEST]`` (#188) copies the ten
notebooks and the README out of the package, writable, and refuses a DEST in use."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import pysuto
from pysuto.__main__ import main
from pysuto.tutorial import PACKAGE_DIR, copy_tutorial

NAMES = ["00_world", "01_datafeed", "02_aggregate_impute", "03_constraints", "04_solver",
         "05_posterior", "06_psut_piot", "07_scoreboard", "08_break_it", "09_bridge"]


def test_the_package_holds_the_ten_notebooks_and_the_readme_and_no_run_output():
    assert sorted(p.name for p in PACKAGE_DIR.glob("*.ipynb")) == [n + ".ipynb" for n in NAMES]
    assert (PACKAGE_DIR / "README.md").is_file()
    assert not (PACKAGE_DIR / "runs").exists()


def test_the_copy_writes_the_notebooks_and_the_readme_into_a_new_folder(tmp_path):
    dest = tmp_path / "new" / "tut"
    written = copy_tutorial(dest)
    assert sorted(p.name for p in dest.iterdir()) == sorted(
        [n + ".ipynb" for n in NAMES] + ["README.md"])
    assert sorted(written) == sorted(dest.iterdir())
    for src in PACKAGE_DIR.glob("*.ipynb"):
        assert (dest / src.name).read_bytes() == src.read_bytes()
    assert all(os.access(p, os.W_OK) for p in written)


def test_the_copies_are_mode_0644_whatever_the_installed_files_are(tmp_path):
    copy_tutorial(tmp_path / "tut")
    modes = {stat.S_IMODE(p.stat().st_mode) for p in (tmp_path / "tut").iterdir()}
    assert modes == {0o644}


def test_an_empty_existing_folder_is_accepted(tmp_path):
    copy_tutorial(tmp_path)
    assert (tmp_path / "00_world.ipynb").is_file()


def test_a_folder_that_is_not_empty_is_refused_and_left_untouched(tmp_path):
    (tmp_path / "mine.txt").write_text("keep")
    with pytest.raises(FileExistsError, match="not an empty directory"):
        copy_tutorial(tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["mine.txt"]


def test_a_file_as_dest_is_refused(tmp_path):
    target = tmp_path / "file"
    target.write_text("x")
    with pytest.raises(FileExistsError):
        copy_tutorial(target)


def test_the_command_defaults_to_pysuto_tutorial_in_the_working_directory(
        tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["tutorial"]) == 0
    assert (tmp_path / "pysuto-tutorial" / "00_world.ipynb").is_file()
    assert "00_world.ipynb" in capsys.readouterr().out


def test_the_command_refuses_a_dest_in_use_with_exit_2(tmp_path):
    (tmp_path / "mine.txt").write_text("keep")
    src = str(Path(pysuto.__file__).resolve().parents[1])
    proc = subprocess.run([sys.executable, "-m", "pysuto", "tutorial", str(tmp_path)],
                          capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": src})
    assert proc.returncode == 2 and "not an empty directory" in proc.stderr
    assert [p.name for p in tmp_path.iterdir()] == ["mine.txt"]
