"""test_own_case.py — the helpers of chapter 10_your_case (#197, ``pysuto.tutorial.toy_ext``):
a params family under the shipped template's header, a feed of one's own, Stage 1 of a case
outside the package, and ``python -m pysuto run`` as a call."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from pysuto.feedpipe import FeedSpec
from pysuto.registry import DataFeedRegistry
from pysuto.tutorial import PACKAGE_DIR, toy_ext

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


ACC = {
    "sectors": [{"name": "Deposit", "entity": "SB", "sub": "Raw", "role": "nature"},
                {"name": "Mill", "entity": "Process"},
                {"name": "Concentrate", "entity": "Flow"},
                {"name": "Use", "entity": "SB", "sub": "Demand", "role": "final_demand"}],
    "regions": ["Aland"],
    "valuations": [{"name": "Gross", "role": "gross"}, {"name": "Content", "role": "content"}],
    "times": ["2001", "2002"],
    "supply": {"Mill": ["Concentrate"]},
    "use": {"Deposit": ["Mill"], "Concentrate": ["Use"]},
    "tradable": [],
    "accounting": [{"from": "Process", "to": "Flow", "same_region": True},
                   {"from": "Flow", "to": "SB", "same_region": False},
                   {"from": "SB", "to": "Process", "same_region": True}],
}


def _write_inputs(root) -> None:
    acc = root / "input" / "acc" / "mycase" / "current"
    feed = root / "input" / "feed" / "gauge" / "current"
    acc.mkdir(parents=True)
    feed.mkdir(parents=True)
    (acc / "acc.json").write_text(json.dumps(ACC))
    pd.DataFrame({"Year": ["2001", "2002"], "Region": "Aland", "Material": "ore feed",
                  "Unit": "kt", "Value": [98.0, 103.5]}).to_csv(feed / "values.csv",
                                                                 index=False)
    tables = {"sector_map": (["ore feed"], ["Deposit"]), "region_map": (["Aland"], ["Aland"]),
              "time_map": (["2001", "2002"], ["2001", "2002"]),
              "valuation_map": (["kt"], ["Gross"])}
    with pd.ExcelWriter(feed / "conc.xlsx") as xl:
        for name, (src, root_) in tables.items():
            key = name[:-4]
            pd.DataFrame({f"src_{key}": src, f"root_{key}": root_}).to_excel(
                xl, sheet_name=name, index=False)
        pd.DataFrame([("Year", "src_time"), ("Material", "src_sector_from"),
                      ("Region", "src_region_from"), ("Region", "src_region_to"),
                      ("Unit", "src_valuation")], columns=["raw_var", "src_var"]
                     ).to_excel(xl, sheet_name="var_map", index=False)


def _load_tables(path) -> dict:
    return pd.read_excel(path, sheet_name=None, dtype=str)


def test_register_feeds_builds_the_acc_and_runs_each_feed_spec_through_run_feed(tmp_path):
    _write_inputs(tmp_path)
    spec = FeedSpec("gauge", load_raw=lambda p: pd.read_csv(p, dtype={"Year": str}),
                    load_tables=_load_tables)
    ids = toy_ext.register_feeds(tmp_path, "mycase", [spec])
    assert list(ids) == ["gauge"]
    assert (tmp_path / "proc" / "acc" / "mycase").is_dir()
    registry = DataFeedRegistry(odir=str(tmp_path / "proc" / "feed" / "registry"))
    registry.load_index()
    sidecar = registry.load_sidecar(ids["gauge"])
    assert sidecar["label"] == "gauge"
    assert sidecar["parents"]["inputs"]["acc"]["id"] == "mycase"


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
