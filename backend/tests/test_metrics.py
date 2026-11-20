import numpy as np
import pytest

from ml.evaluate import user_metrics


def test_all_relevant_found_at_top():
    p, r, n = user_metrics([1, 2, 3, 4, 5], {1, 2}, 5)
    assert p == pytest.approx(0.4)
    assert r == pytest.approx(1.0)
    assert n == pytest.approx(1.0)


def test_no_hits():
    assert user_metrics([1, 2, 3], {9}, 3) == (0.0, 0.0, 0.0)


def test_ndcg_penalises_lower_rank():
    _, _, n = user_metrics([1, 2, 3], {2}, 3)
    assert n == pytest.approx(1 / np.log2(3))


def test_partial_recall():
    p, r, _ = user_metrics([1, 2, 3], {1, 9}, 3)
    assert r == pytest.approx(0.5)
    assert p == pytest.approx(1 / 3)