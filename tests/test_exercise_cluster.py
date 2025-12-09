import unittest

from tbweightcalc.exercise_set import ExerciseSet
from tbweightcalc.exercise_cluster import ExerciseCluster

##############
# UNIT TESTS #
##############


class TestExerciseCluster(unittest.TestCase):
    def test_str(self):
        # ----- Squat: week 1 -----
        c = ExerciseCluster(week=1, exercise=ExerciseCluster.SQUAT, oneRepMax=400)
        out = str(c)
        lines = out.strip().splitlines()

        # There should be multiple sets
        self.assertGreaterEqual(len(lines), 5)

        # Check that there is a light warmup set (2 x 5) with the bar
        self.assertTrue(
            any("2 x 5" in line and "45" in line and "Bar" in line for line in lines),
            "Expected a 2 x 5 warmup set with 45 and 'Bar' in squat cluster output.",
        )

        # Check that the top set for squat week 1 shows (3-5) x 5 and 280 somewhere
        self.assertTrue(
            any("(3-5) x 5" in line and "280" in line for line in lines),
            "Expected a (3-5) x 5 top set with 280 in squat cluster output.",
        )

        # ----- Bench press: week 4 -----
        c = ExerciseCluster(week=4, exercise=ExerciseCluster.BENCHPRESS, oneRepMax=230)
        out = str(c)
        lines = out.strip().splitlines()

        # Expect at least one work set around 170 (top set)
        self.assertTrue(
            any("(3-5) x 5" in line and "170" in line for line in lines),
            "Expected a (3-5) x 5 top set with 170 in bench cluster output.",
        )

        # ----- Deadlift: week 3 -----
        c = ExerciseCluster(week=3, exercise=ExerciseCluster.DEADLIFT, oneRepMax=400)
        out = str(c)
        lines = out.strip().splitlines()

        # Expect a heavy triple around 360 somewhere
        self.assertTrue(
            any("(1-3) x 3" in line and "360" in line for line in lines),
            "Expected a (1-3) x 3 set with 360 in deadlift cluster output.",
        )

        # ----- Weighted pull-ups: week 1, low load -> bodyweight only -----
        c = ExerciseCluster(
            week=1, exercise=ExerciseCluster.WPU, oneRepMax=240, body_weight=180
        )
        out = str(c).strip()

        # For low loads we expect just bodyweight text, no plate breakdown
        self.assertIn("Bodyweight", out)

        # ----- Weighted pull-ups: week 3, heavier load -> show added weight -----
        c = ExerciseCluster(
            week=3, exercise=ExerciseCluster.WPU, oneRepMax=240, body_weight=180
        )
        out = str(c).strip()
        # Should show the added weight (here 35) in some form
        self.assertIn("35", out)

        # ----- Weighted pull-ups: week 6, heavier again -> show plates, not bar -----
        c = ExerciseCluster(
            week=6, exercise=ExerciseCluster.WPU, oneRepMax=300, body_weight=180
        )
        out = str(c).strip()

        # Should show the added weight (around 105) somewhere
        self.assertIn("105", out)
        # Should show some plate breakdown (e.g. (45 x 2)), but not say "Bar"
        self.assertIn("45", out)
        self.assertNotIn(
            "Bar", out, msg="WPU should not include bar weight in description."
        )

    def test_get_item(self):
        # Cluster indexing should return individual sets in order
        c = ExerciseCluster(exercise=ExerciseCluster.SQUAT, oneRepMax=425)

        first = str(c[0])
        last = str(c[-1])

        # First set should look like a light warmup: 2 x 5, bar weight
        self.assertIn("2 x 5", first)
        self.assertIn("45", first)
        self.assertIn("Bar", first)

        # Last set should be the heaviest top set with (3-5) x 5 and ~300
        self.assertIn("(3-5) x 5", last)
        self.assertIn("300", last)
        # Should include some plate breakdown (e.g. (45 x 2) ...)
        self.assertIn("45", last)

    def test_week_setter(self):
        # When week is set, label and multiplier should update
        c = ExerciseCluster(exercise=ExerciseCluster.SQUAT, oneRepMax=425, week=1)
        self.assertEqual(c.week, 1)
        self.assertEqual(c.week_multiplier, 0.70)
        self.assertEqual(c.label, "70%")

        c.week = 2
        self.assertEqual(c.week, 2)
        self.assertEqual(c.week_multiplier, 0.80)
        self.assertEqual(c.label, "80%")

        c.week = 3
        self.assertEqual(c.week, 3)
        self.assertEqual(c.week_multiplier, 0.90)
        self.assertEqual(c.label, "90%")

        c.week = 4
        self.assertEqual(c.week, 4)
        self.assertEqual(c.week_multiplier, 0.75)
        self.assertEqual(c.label, "75%")

        c.week = 5
        self.assertEqual(c.week, 5)
        self.assertEqual(c.week_multiplier, 0.85)
        self.assertEqual(c.label, "85%")

        c.week = 6
        self.assertEqual(c.week, 6)
        self.assertEqual(c.week_multiplier, 0.95)
        self.assertEqual(c.label, "95%")

        # Week 7+ currently not defined, should return week 1
        c.week = 7
        self.assertEqual(c.week, 1)
        self.assertEqual(c.week_multiplier, 0.70)
        self.assertEqual(c.label, "70%")

    def test_label(self):
        c = ExerciseCluster(week=1)
        self.assertEqual(c.label, "70%")

        c = ExerciseCluster(week=6)
        self.assertEqual(c.label, "95%")

    def test_working_weight(self):
        c = ExerciseCluster(week=2, oneRepMax=403)
        self.assertEqual(c.working_weight, 320)

    def test_add(self):
        c = ExerciseCluster()
        s1 = ExerciseSet()
        s2 = ExerciseSet()

        c.add(s1)
        c.add(s2)

        self.assertEqual(c[0], s1)
        self.assertEqual(c[1], s2)

    def test_calc_sets(self):

        # Custom weight sets.
        s = ExerciseSet(weight=275)  # Bar should be included in weight.
        self.assertEqual(s.calc_plate_breakdown([45, 25, 10, 5, 2.5]), "(45 x 2) 25")

        s = ExerciseSet(weight=245)
        self.assertEqual(s.calc_plate_breakdown([100, 45, 25, 10, 5, 2.5]), "100")

        s = ExerciseSet(weight=45)
        self.assertEqual(s.calc_plate_breakdown([45, 25, 10, 5, 2.5]), "Bar")

        s = ExerciseSet(weight=240)
        self.assertEqual(
            s.calc_plate_breakdown([55, 45, 35, 25, 10, 5, 2.5]), "55 35 5 2.5"
        )

        s = ExerciseSet(bar_weight=35, weight=240)
        self.assertEqual(
            s.calc_plate_breakdown([55, 45, 35, 25, 10, 5, 2.5]), "55 45 2.5"
        )

        # TODO: what happens if bad plate list is given? 1.24 24# etc? Must include 1.25 plates though.
        # s = ExerciseSet(weight=242.5)
        # self.assertEqual(s.calc_plate_breakdown([45,35,25,10,5,2.5, 1.25]), "???")


#############
# RUN TESTS #
#############

if __name__ == "__main__":
    unittest.main()
