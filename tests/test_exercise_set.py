from tbweightcalc.exercise_set import ExerciseSet

import unittest

##############
# UNIT TESTS #
##############


class TestExerciseSet(unittest.TestCase):

    class TestExerciseSet(unittest.TestCase):
        def _normalize_weight(self, s: str) -> str:
            # Treat " lbs" and "#" as equivalent for tests
            return s.replace(" lbs", "#")

        def test_to_str(self):
            # Returns correctly formatted set string.

            # Tests default max sets and reps to 5x5
            s = ExerciseSet(weight=425)
            out = self._normalize_weight(str(s))
            self.assertEqual(out, "5 x 5 - 425# - (45 x 4) 10")

            # Tests different min and max sets / reps
            s = ExerciseSet(weight=425, min_set=3, min_reps=3)
            out = self._normalize_weight(str(s))
            self.assertEqual(out, "(3-5) x (3-5) - 425# - (45 x 4) 10")

            s = ExerciseSet(weight=425, min_set=1, max_set=10, min_reps=3, max_reps=15)
            out = self._normalize_weight(str(s))
            self.assertEqual(out, "(1-10) x (3-15) - 425# - (45 x 4) 10")

            # Test default
            s = ExerciseSet()
            out = self._normalize_weight(str(s))
            self.assertEqual(out, "5 x 5 - 0# - Bar")

        def test_weight_setter(self):
            # Updates plate breakdown when weight is set.
            s = ExerciseSet(weight=300)
            self.assertEqual(s.plate_breakdown, "(45 x 2) 35 2.5")

            # Change weight, should update.
            s.weight = 500
            self.assertEqual(s.plate_breakdown, "(45 x 5) 2.5")

        def test_set(self):
            # Should return max sets
            s = ExerciseSet(max_set=8)
            self.assertEqual(s.set, 8)

        def test_reps(self):
            # reps should return max reps
            s = ExerciseSet(max_reps=10)
            self.assertEqual(s.reps, 10)

        def test_bar_weight(self):

            # Test default bar weight.
            s = ExerciseSet()
            self.assertEqual(s.bar_weight, 45)

            s = ExerciseSet(bar_weight=55)
            self.assertEqual(s.bar_weight, 55)

            s.bar_weight = 35
            self.assertEqual(s.bar_weight, 35)

        def test_calc_lifting_weight(self):
            s = ExerciseSet()

            # Check weight gets rounded.
            s.calc_lifting_weight(133, 1.0)
            self.assertEqual(s.weight, 135)

            # If weight is 0, set to barweight
            s.calc_lifting_weight(0, 1.0)
            self.assertEqual(s.weight, s.bar_weight)

            # If weight is 45, set to barweight (default is 45)
            s.calc_lifting_weight(45, 1.0)
            self.assertEqual(s.weight, s.bar_weight)

            # Properly calculates lifting weight * multiplier
            s.calc_lifting_weight(225, 0.85)
            self.assertEqual(s.weight, 190)

            s.calc_lifting_weight(225, 0.55)
            self.assertEqual(s.weight, 125)

        def test_calc_weighted_pullup(self):
            s = ExerciseSet(bar=False)

            # Weight should = working weight * multiplier - bodyweight
            s.calc_weighted_pullup(260, 200, 1.0)
            self.assertEqual(s.weight, 60)
            self.assertEqual(s.plate_breakdown, "45 15")

            s.calc_weighted_pullup(260, 200, 0.90)
            self.assertEqual(s.weight, 34)
            self.assertEqual(s.plate_breakdown, "35")

            # If weight returns negative => 0
            s.calc_weighted_pullup(260, 200, 0.75)
            self.assertEqual(s.weight, 0)
            self.assertEqual(s.plate_breakdown, "Bodyweight")

        def test_calc_platebreakdown(self):
            # Rounds weight and returns proper breakdown
            s = ExerciseSet(weight=400)
            self.assertEqual(s.plate_breakdown, "(45 x 3) 35 5 2.5")
            s.weight = 135
            self.assertEqual(s.plate_breakdown, "45")
            s.weight = 150
            self.assertEqual(s.plate_breakdown, "45 5 2.5")

            # If weight <= 45, return 'Bar'
            s = ExerciseSet(weight=45)
            self.assertEqual(s.plate_breakdown, "Bar")
            s.weight = -1
            s.bar = True
            self.assertEqual(s.plate_breakdown, "Bar")

            # Breakdown plate breakdown if bar == False and weight less 45
            s = ExerciseSet(bar=False, weight=45)
            self.assertEqual(s.plate_breakdown, "45")

            s.weight = 25
            self.assertEqual(s.plate_breakdown, "25")

            # Return bodyweight if weight <= 0 and bar == False
            s = ExerciseSet(weight=-1, bar=False)
            self.assertEqual(s.plate_breakdown, "Bodyweight")

            s.weight = 0
            self.assertEqual(s.plate_breakdown, "Bodyweight")

            # If weight > 45 and bar == False
            s.weight = 105
            self.assertEqual(s.plate_breakdown, "(45 x 2) 15")

            # TODO: Test plate breakdown with custom plates ie 55#, 100#, etc

        def test_round_weight(self):
            # Rounds to nearest increment of 5
            self.assertEqual(ExerciseSet.round_weight(8), 10, "8 => 10")
            self.assertEqual(ExerciseSet.round_weight(6), 5, "6 => 5")
            self.assertEqual(ExerciseSet.round_weight(1), 0, "1 => 0")
            self.assertEqual(ExerciseSet.round_weight(4), 5, "4 => 5")
            self.assertEqual(ExerciseSet.round_weight(-1), 0, "-1 => 0")
            self.assertEqual(ExerciseSet.round_weight(257), 255, "257 => 255")
            self.assertEqual(ExerciseSet.round_weight(343.23), 345)

        def test_plate_breakdown_on(self):
            s = ExerciseSet(weight=230)
            out = str(s)

            # Accept *either* lbs or #
            self.assertTrue(out.startswith("5 x 5 - 230"), f"Unexpected prefix: {out}")

            # Plate breakdown must still be correct
            self.assertIn("(45 x 2) 2.5", out)

            # Test setter
            s.plate_breakdown_on = False
            out = str(s)
            self.assertTrue(out.startswith("5 x 5 - 230"))
            self.assertNotIn("(45 x 2)", out)

            # Test init
            s = ExerciseSet(weight=230, plate_breakdown_on=False)
            out = str(s)
            self.assertTrue(out.startswith("5 x 5 - 230"))
            self.assertNotIn("(45 x 2)", out)


import tbweightcalc.exercise_set as es


class TestOptimizeWarmupWeight:
    def test_does_nothing_for_bar_only_or_lighter(self):
        assert es.optimize_warmup_weight(45) == 45
        assert es.optimize_warmup_weight(40) == 40

    def test_rounds_up_within_threshold_to_next_plate(self):
        # total = 90 lb (45 bar + 22.5/side)
        # per-side = 22.5, next plate = 25
        # 25 - 22.5 = 2.5 <= threshold -> bump to 95 total
        result = es.optimize_warmup_weight(90)
        assert result == 95

    def test_does_not_round_if_gap_is_too_large(self):
        # total = 100 lb -> per-side = 27.5
        # next plate = 35 -> gap = 7.5 > 2.5 -> no change
        result = es.optimize_warmup_weight(100)
        assert result == 100

    def test_respects_custom_threshold(self):
        # total = 90 lb -> per-side = 22.5
        # next plate = 25 -> gap = 2.5
        # with threshold = 2.0, should NOT bump
        result = es.optimize_warmup_weight(90, threshold=2.0)
        assert result == 90

    def test_uses_custom_available_plates(self):
        # available plates only 45 and 10
        # total = 65 lb -> per-side = 10
        # exact match to 10 plate -> stays 65
        result = es.optimize_warmup_weight(
            65,
            bar_weight=45,
            available_plates=[45, 10],
        )
        assert result == 65

        # total = 60 lb -> per-side = 7.5
        # next plate = 10, gap = 2.5 -> bump to 65
        result2 = es.optimize_warmup_weight(
            60,
            bar_weight=45,
            available_plates=[45, 10],
        )
        assert result2 == 65


import tbweightcalc.exercise_set as es


class TestOptimizeWarmupWeight:
    def test_does_nothing_for_bar_only_or_lighter(self):
        assert es.optimize_warmup_weight(45) == 45
        assert es.optimize_warmup_weight(40) == 40

    def test_rounds_small_warmup_to_next_plate_around_25(self):
        # total = 90 lb (45 bar + 22.5/side)
        # per-side = 22.5
        # base_plate = 15, remainder = 7.5
        # next plate >= 7.5 is 10, gap = 2.5 -> per-side 25, total 95
        result = es.optimize_warmup_weight(90)
        assert result == 95

    def test_rounds_45_15_5_2_5_to_45_25(self):
        """
        180 total = 45 bar + (45+15+5+2.5) per side

        per-side = 67.5
        base_plate = 45
        remainder = 22.5
        next plate >= 22.5 is 25 (gap = 2.5)

        -> per-side = 45 + 25 = 70
        -> total = 45 + 2*70 = 185
        """
        result = es.optimize_warmup_weight(180)
        assert result == 185

    def test_does_not_round_if_gap_is_too_large(self):
        # total = 100 lb -> per-side = 27.5
        # base_plate = 25, remainder = 2.5
        # next plate >= 2.5 is 2.5 (exact match) -> stays 100
        result = es.optimize_warmup_weight(100)
        assert result == 100

        # With a tighter threshold, 90 should also stay 90
        result2 = es.optimize_warmup_weight(90, threshold=2.0)
        assert result2 == 90

    def test_respects_custom_available_plates(self):
        # Only 10-lb small plates available (plus bar)
        # total = 60 -> per-side = 7.5
        # base_plate = 0, remainder = 7.5
        # next plate >= 7.5 is 10, gap = 2.5 -> total becomes 65
        result = es.optimize_warmup_weight(
            60,
            bar_weight=45,
            available_plates=[45, 10],
        )
        assert result == 65


import tbweightcalc.exercise_set as es


class TestOptimizeWarmupWeight:
    def test_does_nothing_for_bar_only_or_lighter(self):
        assert es.optimize_warmup_weight(45) == 45
        assert es.optimize_warmup_weight(40) == 40

    def test_rounds_small_warmup_to_next_plate_around_25(self):
        # 90 total -> per-side = (90 - 45)/2 = 22.5
        # base_total = 0, remainder = 22.5
        # next plate >= 22.5 is 25 (gap 2.5) -> total 95
        result = es.optimize_warmup_weight(90)
        assert result == 95

    def test_rounds_single_45_with_small_plates_to_45_and_25(self):
        """
        180 total = 45 bar + (45+15+5+2.5) per side

        per-side     = 67.5
        base_total   = 45 (one 45 peeled off)
        remainder    = 22.5
        next plate   = 25 (gap = 2.5)

        -> per-side  = 45 + 25 = 70
        -> total     = 45 + 2*70 = 185
        """
        result = es.optimize_warmup_weight(180)
        assert result == 185

    def test_rounds_double_45_with_small_plates_to_45x2_and_35(self):
        """
        290 total = 45 bar + (45+45+25+5+2.5) per side

        per-side     = (290 - 45)/2 = 122.5
        peel 45s     = base_total = 90, remainder = 32.5
        next plate   = 35 (gap = 2.5)

        -> per-side  = 90 + 35 = 125
        -> total     = 45 + 2*125 = 295
        """
        result = es.optimize_warmup_weight(290)
        assert result == 295

    def test_does_not_round_if_gap_is_too_large(self):
        # total = 100 -> per-side = 27.5
        # base_total = 0, remainder = 27.5
        # next plate = 35 (gap = 7.5 > 2.5) -> stays 100
        result = es.optimize_warmup_weight(100)
        assert result == 100

    def test_respects_custom_available_plates(self):
        # Only 10-lb plates (plus bar)
        # 60 total -> per-side = 7.5
        # base_total = 0, remainder = 7.5
        # next plate = 10 (gap 2.5) -> total 65
        result = es.optimize_warmup_weight(
            60,
            bar_weight=45,
            available_plates=[45, 10],
        )
        assert result == 65

    def test_optimize_with_custom_plates_55_45_25_10_5(self):
        # Example: bar 45 + per side (45 + 10 + 5) = 65 per side => 175 total
        # Let’s say this is a warm-up and we want to see if 10+5 (15) bumps to 25.
        #
        # per-side = (175 - 45)/2 = 65
        # largest = 55 -> per-side-55 = 10 < 55 so base_total = 55, remainder = 10
        # next plate >= 10 is 10 (gap = 0) so no change: stays 175.
        #
        # Now try 45 + 15 per side: 45 + 15 = 60 per side => 165 total
        # per-side = 60, base_total = 55, remainder = 5
        # next plate >= 5 is 5 (gap = 0) -> stays 165.
        #
        # But for something like (45 + 10 + 10) = 65 per side => 175 total:
        # remainder = 10, and 25 is > 10 with gap 15 -> > threshold, no bump.
        #
        # This test mainly ensures function doesn't blow up and respects the plate set.
        result = es.optimize_warmup_weight(
            165,
            bar_weight=45,
            available_plates=[55, 45, 25, 10, 5],
        )
        assert result == 165

    def test_rounds_up_to_match_next_big_plate(self):
        # Current warm-up: 120 total -> per-side = 37.5 (35 + 2.5)
        # Next set: 165 total -> per-side = 60 (will use a 45)
        # With lookahead, the 120 set should round up to 135 (a single 45/side)
        result = es.optimize_warmup_weight(120, next_total_weight=165)
        assert result == 135

    def test_does_not_force_big_plate_when_too_far(self):
        # Current warm-up: 95 total -> per-side = 25
        # Next set: heavy enough for 45s, but gap is 20 lb/side (> big_plate_slack)
        result = es.optimize_warmup_weight(95, next_total_weight=225)
        assert result == 95
