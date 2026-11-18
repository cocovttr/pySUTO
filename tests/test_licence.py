"""test_licence.py
===============
The code is MIT, the hand-authored tables CC BY 4.0, and the citation file names the
author (#193).
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_the_code_licence_is_mit():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("MIT License")
    assert "Copyright (c) 2026 Florian Huber" in text


def test_the_tables_licence_is_cc_by_4():
    text = (ROOT / "LICENSE-DATA").read_text(encoding="utf-8")
    assert "CC BY 4.0" in text and "data/input/" in text


def test_the_citation_file_names_the_author_and_the_licence():
    cff = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    assert cff["cff-version"] == "1.2.0" and cff["license"] == "MIT"
    (author,) = cff["authors"]
    assert (author["given-names"], author["family-names"]) == ("Florian", "Huber")
    assert author["orcid"] == "https://orcid.org/0009-0000-4927-3104"


def test_the_readmes_name_both_licences():
    for name in ("README.md", "README_PYPI.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "MIT" in text, name
    assert "CC BY 4.0" in (ROOT / "README.md").read_text(encoding="utf-8")
