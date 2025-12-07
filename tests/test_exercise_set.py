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


#############
# RUN TESTS #
#############

if __name__ == "__main__":
    unittest.main()
