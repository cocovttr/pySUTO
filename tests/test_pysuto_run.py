"""test_pysuto_run.py — ``python -m pysuto run`` (#125): the toy case's six stages in one
command, under its own labels.

One module-scoped chain runs ``python -m pysuto run --case toy --from feed --to psut
--data-dir <tmp>`` as a subprocess from an empty working directory, which must hold no
``data/`` afterwards. The result is read back through the registries, its sidecars'
parents are walked from the PSUT to the feeds, and the toy's own checks of
``test_toy_case.py`` run on it (hard rows close, the planted leg is the top soft
residual, Stage 5 coverage lies in its recorded band, the PSUT balances). The command's
argument handling and the step commands are checked without running a driver.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import test_toy_case as toy_checks
from pysuto.acc import AccountingStructure
from pysuto.cases import toy
from pysuto.pipeline import ALL_STEPS, Chain, Pipeline
from pysuto.registry import (ConstraintRunRegistry, DataFeedRegistry,
                             ImputationRunRegistry, OptimRunRegistry, PsutRunRegistry,
                             UncPropRunRegistry)

REPO = Path(__file__).resolve().parents[1]


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "pysuto", "run", *args], cwd=str(cwd),
                          capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": str(REPO / "src")})


@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    root, cwd = tmp_path_factory.mktemp("toy_data"), tmp_path_factory.mktemp("cwd")
    proc = _run(cwd, "--case", "toy", "--from", "feed", "--to", "psut",
                "--data-dir", str(root))
    assert proc.returncode == 0, f"{proc.stdout[-1500:]}\n{proc.stderr[-3000:]}"
    printed = {line.split()[0]: line.split()[1:] for line in proc.stdout.splitlines()}
    ids = {"feed": dict(zip(toy.FEED_IDS, printed["feed"]))}
    ids.update({s: printed[s][0] for s in ("imp", "const", "opt", "uncprop", "psut")})
    return {"root": root, "cwd": cwd, "ids": ids, "stdout": proc.stdout,
            "acc": AccountingStructure.load(toy.ACC_ID,
                                            storage_dir=str(root / "proc" / "acc"))}


def test_the_command_leaves_six_stages_linked_through_their_sidecars(chain):
    root, ids = chain["root"], chain["ids"]
    proc = root / "proc"
    assert not (chain["cwd"] / "data").exists()
    regs = {"imp": ImputationRunRegistry, "const": ConstraintRunRegistry,
            "opt": OptimRunRegistry, "uncprop": UncPropRunRegistry,
            "psut": PsutRunRegistry}
    side = {s: r(str(proc / s)).load_sidecar(ids[s]) for s, r in regs.items()}
    for stage in regs:
        assert (proc / stage / ids[stage]).is_dir()
    for run_id in ids["feed"].values():
        assert run_id.startswith("feed_") and (proc / "feed" / "registry" / run_id).is_dir()
    assert side["imp"]["parents"]["upstream"]["feed_run_ids"] == list(ids["feed"].values())
    assert side["const"]["parents"]["upstream"]["imp_run_id"] == ids["imp"]
    assert side["opt"]["parents"]["upstream"]["const_run_id"] == ids["const"]
    assert side["uncprop"]["parents"]["upstream"]["opt_run_id"] == ids["opt"]
    assert side["psut"]["parents"]["upstream"]["opt_run_id"] == ids["opt"]
    for stage, sidecar in side.items():
        assert sidecar["label"] == "toy" and \
            sidecar["stage_config"]["case"]["id"] == "toy", stage


def test_the_toy_s_checks_hold_on_the_one_command_chain(chain):
    toy_checks.test_every_hard_row_closes_to_1e_10(chain)
    toy_checks.test_the_planted_leg_is_the_top_soft_residual(chain)
    toy_checks.test_stage5_coverage_of_the_420_edges_lies_in_its_recorded_band(chain)
    toy_checks.test_the_psut_supply_and_use_blocks_balance_per_node(chain)


def test_a_feed_step_needs_the_case_s_stage_1_hook(tmp_path):
    from dataclasses import replace
    with pytest.raises(ValueError, match="declares none"):
        Pipeline(steps=ALL_STEPS, case=replace(toy.CASE, stage1=None),
                 data_dir=str(tmp_path))


def test_a_start_past_the_feed_step_needs_a_base_and_a_feed_start_refuses_one(tmp_path):
    no_base = _run(tmp_path, "--case", "toy", "--from", "imp", "--data-dir", str(tmp_path))
    assert no_base.returncode == 2 and "--base" in no_base.stderr
    both = _run(tmp_path, "--case", "toy", "--from", "feed", "--base", "opt_x",
                "--data-dir", str(tmp_path))
    assert both.returncode == 2 and "--base" in both.stderr
    back = _run(tmp_path, "--case", "toy", "--from", "opt", "--to", "imp",
                "--data-dir", str(tmp_path))
    assert back.returncode == 2 and "comes after" in back.stderr


def test_the_command_runs_all_six_stages_in_process_with_no_scripts_directory(
        tmp_path, monkeypatch, capsys):
    """#186: the steps call ``pysuto.stages`` with the case object; no driver script is
    looked up and no subprocess is spawned."""
    import pysuto.pipeline as pipeline_module
    from pysuto.__main__ import main

    def spawn(*a, **k):
        raise AssertionError(f"a subprocess was spawned: {a!r}")

    for name in ("run", "Popen", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, spawn)
    monkeypatch.chdir(tmp_path)
    assert main(["run", "--case", "toy", "--data-dir", str(tmp_path / "d")]) == 0
    assert not hasattr(pipeline_module, "REPO_ROOT")
    printed = {l.split()[0] for l in capsys.readouterr().out.splitlines() if l.split()}
    assert {"feed", "imp", "const", "opt", "uncprop", "psut"} <= printed
    for stage in ("imp", "const", "opt", "uncprop", "psut"):
        assert len(list((tmp_path / "d" / "proc" / stage).glob(f"{stage}_*"))) == 1


def test_a_step_receives_the_case_object_and_the_config_only_for_imp_and_const(
        tmp_path, monkeypatch):
    import pysuto.pipeline as pipeline_module
    seen = {}

    def fake(step):
        def run(case, *args, **kwargs):
            seen[step] = (case, kwargs)
            return f"{step}_x"
        return run

    for step, name in (("imp", "run_imp"), ("const", "run_const"), ("opt", "run_opt"),
                       ("uncprop", "run_uncprop"), ("psut", "run_psut")):
        monkeypatch.setattr(pipeline_module, name, fake(step))
    cfg = tmp_path / "c.yaml"
    cfg.write_text("pipeline:\n  acc_id: other\n")
    base = Chain(feed_run_ids=("feed_a",), imp="imp_1", const="const_1", opt="opt_1")
    pipe = Pipeline(steps=ALL_STEPS[1:], base=base, case=toy.CASE, data_dir="d",
                    config=str(cfg), cwd=str(tmp_path), log_dir=str(tmp_path / "logs"))
    chain = pipe.run({}, label="lbl")
    assert chain.psut == "psut_x"
    for step, (case, kwargs) in seen.items():
        assert kwargs["data_dir"] == str(tmp_path / "d"), step
        assert case.acc_id == ("other" if step in ("imp", "const") else toy.CASE.acc_id)
        assert step in ("imp", "const") or case is toy.CASE
    with pytest.raises(KeyError, match="uncprop step takes no knobs"):
        pipe.check_overrides({"uncprop.ALPHA": 0.1})
