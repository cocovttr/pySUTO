"""test_own_case.py — the helpers of chapter 10_your_case (#197, ``pysuto.tutorial.toy_ext``):
a params family under the shipped template's header, a feed of one's own, Stage 1 of a case
outside the package, and ``python -m pysuto run`` as a call."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from pysuto.registry import DataFeedRegistry
from pysuto.tutorial import PACKAGE_DIR, toy, toy_ext

TEMPLATE = PACKAGE_DIR / "params_template.csv"


def _frame(path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)


def test_the_template_ships_beside_the_notebooks():
    assert TEMPLATE.is_file()
    assert TEMPLATE.read_text(encoding="utf-8").startswith("param_id;param_type;")


def test_a_family_keeps_the_templates_columns_and_none_of_its_examples(tmp_path):
    rows = [{"param_id": "effmill", "param_type": "efficiency", "value_nominal": "0.9"}]
    path = toy_ext.params_from_template(TEMPLATE, rows, tmp_path / "eff" / "params.csv")
    frame = _frame(path)
    header = TEMPLATE.read_text(encoding="utf-8").splitlines()[0].split(";")
    assert list(frame.columns) == header
    assert frame["param_id"].tolist() == ["effmill"]
    assert frame.loc[0, "value_nominal"] == "0.9" and frame.loc[0, "source"] == ""
    assert "#" not in path.read_text(encoding="utf-8")


def test_a_row_naming_a_column_the_template_lacks_raises_and_writes_nothing(tmp_path):
    with pytest.raises(KeyError, match="agg"):
        toy_ext.params_from_template(TEMPLATE, [{"param_id": "x", "agg": "true"}],
                                     tmp_path / "params.csv")
    assert not (tmp_path / "params.csv").exists()


def test_a_feed_of_ones_own_maps_the_years_it_holds_and_carries_its_pedigree():
    raw = pd.DataFrame({"Year": ["2001", "2002"], "Region": "Aland", "Material": "ore",
                        "Unit": "kt", "Value": [1.0, 2.0]})
    maps = dict(sectors={"ore": "Deposit"}, regions={"Aland": "Aland"},
                units={"kt": "Gross"}, variables=[("Year", "src_time")])
    feed = toy_ext.own_feed("gauge", raw, **maps)
    assert feed.feed_id == feed.metadata.feed_name == "gauge"
    assert feed.maps["time_map_df"]["src_time"].tolist() == ["2001", "2002"]
    good = toy_ext.own_feed("gauge", raw, scores=(1, 1, 1, 1, 1), **maps)
    assert (good.metadata.to_pedigree_scores().total_cv()
            < feed.metadata.to_pedigree_scores().total_cv())


def test_stage1_builds_the_acc_from_the_registered_spec_and_registers_each_feed(tmp_path):
    toy.write_inputs(tmp_path)
    feed = toy.make_feeds(toy.truth())["survey"]
    ids = toy_ext.stage1(tmp_path, toy.ACC_ID, {"survey": feed}, seed=7)
    assert list(ids) == ["survey"]
    assert (tmp_path / "proc" / "acc" / toy.ACC_ID).is_dir()
    registry = DataFeedRegistry(odir=str(tmp_path / "proc" / "feed" / "registry"))
    registry.load_index()
    sidecar = registry.load_sidecar(ids["survey"])
    assert sidecar["label"] == "survey" and sidecar["stage_config"]["seed"] == 7


def test_run_case_takes_a_path_and_returns_the_run_ids_the_command_printed(
        tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "my_toy.py").write_text("from pysuto.tutorial.toy import CASE\n")
    ids = toy_ext.run_case("./my_toy.py", "runs/my_toy", "--to", "imp")
    assert set(ids) == {"feed", "imp", "const", "opt", "uncprop", "psut"}
    assert ids["imp"].startswith("imp_") and ids["const"] == ""
    sidecar = json.loads((tmp_path / "runs" / "my_toy" / "proc" / "imp" / ids["imp"]
                          / "metadata.json").read_text())
    source = sidecar["stage_config"]["case"]["case_source"]
    assert source == f"path:{(tmp_path / 'my_toy.py').resolve()}"


def test_run_case_raises_with_the_end_of_stderr_when_the_command_fails(
        tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="exited 2"):
        toy_ext.run_case("./missing.py", "runs/x")


def test_check_10_1_accepts_the_tables_value_to_one_percent_and_rejects_another():
    table = pd.DataFrame({"period": ["2002"] * 2, "valuation": ["Content", "Gross"],
                          "to_sector": ["Tailings"] * 2, "val": [0.155, 10.35]})
    assert toy_ext.check_10_1(table, 0.1551).startswith("✓ 10.1")
    with pytest.raises(AssertionError):
        toy_ext.check_10_1(table, 0.17)
    with pytest.raises(ValueError, match="found 0"):
        toy_ext.check_10_1(table, 0.155, year="1999")
