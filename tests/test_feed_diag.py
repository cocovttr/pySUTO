"""test_feed_diag.py
=================
The feed diagnostic's histogram bins on data whose range is below float resolution.
"""
from __future__ import annotations

import numpy as np

from pysuto.diag.feed import _hist_bins


def test_cvs_a_few_ulps_apart_get_one_bin_numpy_can_draw():
    # A feed with one cv for every row gives CV_root values a few ulps apart; NumPy 2
    # refuses to cut that range into 30 finite bins ("Too many bins for data range").
    cv = 10.43 + np.arange(3) * np.spacing(10.43)
    assert _hist_bins(cv, 30) == 1
    counts, _ = np.histogram(cv, bins=_hist_bins(cv, 30))
    assert counts.tolist() == [3]


def test_equal_values_get_one_bin():
    assert _hist_bins(np.full(4, 10.43), 30) == 1


def test_a_spread_range_keeps_the_requested_bins():
    assert _hist_bins(np.array([0.5, 12.0, 40.0]), 30) == 30
