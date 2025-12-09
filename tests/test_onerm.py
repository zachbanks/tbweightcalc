from __future__ import annotations

import pytest

from tbweightcalc.onerm import calculate_one_rm


class TestEstimateOneRm:
    def test_basic_single_rep(self):
        # 1 rep should give back essentially the same weight
        assert calculate_one_rm(200, 1) == 200

    def test_multiple_reps_increases_estimate(self):
        # Epley: 1RM = weight * (1 + reps / 30)
        # Example: 300 x 5 -> 300 * (1 + 5/30) = 300 * 7/6 = 350
        assert calculate_one_rm(300, 5) == 350

    def test_rounding_to_nearest_pound(self):
        # 275 x 5 -> 275 * (1 + 5/30) = 275 * 7/6 = 1925/6 ≈ 320.83 -> 321
        assert calculate_one_rm(275, 5) == 321

    def test_invalid_weight_raises(self):
        with pytest.raises(ValueError):
            calculate_one_rm(0, 5)
        with pytest.raises(ValueError):
            calculate_one_rm(-100, 3)

    def test_invalid_reps_raises(self):
        with pytest.raises(ValueError):
            calculate_one_rm(225, 0)
        with pytest.raises(ValueError):
            calculate_one_rm(225, -2)
