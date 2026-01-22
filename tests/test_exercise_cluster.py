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


import pytest
from tbweightcalc.exercise_cluster import ExerciseCluster, EXERCISE_PROFILES


def test_profile_exists_for_new_exercises():
    assert "overhead press" in EXERCISE_PROFILES
    assert "front squat" in EXERCISE_PROFILES
    assert "zercher squat" in EXERCISE_PROFILES
    assert "zercher deadlift" in EXERCISE_PROFILES
    assert "trap bar deadlift" in EXERCISE_PROFILES
    assert "rdl" in EXERCISE_PROFILES


def test_front_squat_generates_sets():
    c = ExerciseCluster(week=1, exercise="front squat", oneRepMax=300)

    # Should behave like a squat-style lift: 4 warmups + 1 top set
    assert len(c.sets) == 5

    text = str(c)
    # Warmup pattern present
    assert "2 x 5" in text
    # Top set pattern like (3-5) x 5
    assert "(3-5) x 5" in text


def test_zercher_squat_generates_sets():
    c = ExerciseCluster(week=1, exercise="zercher squat", oneRepMax=315)

    # Should behave like a squat-style lift: 4 warmups + 1 top set
    assert len(c.sets) == 5

    text = str(c)
    # Warmup pattern present
    assert "2 x 5" in text
    # Top set pattern like (3-5) x 5
    assert "(3-5) x 5" in text


def test_zercher_deadlift_uses_deadlift_scheme():
    c = ExerciseCluster(week=1, exercise="zercher deadlift", oneRepMax=405)

    # Deadlift style: 3 warmups + 1 top set
    assert len(c.sets) == 4

    text = str(c)
    # Deadlift warmup pattern (no bar-only set)
    assert "2 x 5" in text
    # Top set pattern like (1-3) x 5
    assert "(1-3) x 5" in text


def test_trap_bar_deadlift_uses_deadlift_scheme():
    c = ExerciseCluster(week=1, exercise="trap bar deadlift", oneRepMax=500)

    # Deadlift style: 3 warmups + 1 top set
    assert len(c.sets) == 4

    text = str(c)
    # Deadlift warmup pattern
    assert "2 x 5" in text
    # Top set pattern like (1-3) x 5
    assert "(1-3) x 5" in text


def test_rdl_uses_deadlift_scheme():
    c = ExerciseCluster(week=1, exercise="rdl", oneRepMax=365)

    # Deadlift style: 3 warmups + 1 top set
    assert len(c.sets) == 4

    text = str(c)
    # Deadlift warmup pattern (no bar-only set)
    assert "2 x 5" in text
    # Top set pattern like (1-3) x 5
    assert "(1-3) x 5" in text


def test_ohp_uses_bench_style_warmups():
    c = ExerciseCluster(week=1, exercise="overhead press", oneRepMax=200)

    # Should have at least the 4 warmups + 1 top set
    assert len(c.sets) >= 4

    # At least one non-zero warmup weight before the final top set
    warmup_weights = [s.weight for s in c.sets[:-1]]
    assert any(w > 0 for w in warmup_weights)


def test_unknown_exercise_returns_empty():
    c = ExerciseCluster(week=1, exercise="does_not_exist", oneRepMax=200)
    assert c.sets == []


def test_top_sets_follow_week_pattern():
    c3 = ExerciseCluster(week=3, exercise="squat", oneRepMax=400)
    c6 = ExerciseCluster(week=6, exercise="squat", oneRepMax=400)
    assert any("3-4" in str(s) for s in c3.sets)  # week 3 → 3–4 sets
    assert any("1-2" in str(s) for s in c6.sets)  # week 6 → 1–2 reps


def test_bench_warmup_rounds_up_for_next_big_plate():
    """If the next set needs 45s, the prior warmup should load them early."""

    c = ExerciseCluster(week=1, exercise=ExerciseCluster.BENCHPRESS, oneRepMax=345)

    # Bench warmups (4 total) should round the second warmup (0.5 multiplier)
    # up from 120 to 135 so the 45s stay on for the next set.
    warmup_weights = [s.weight for s in c.sets[:4]]
    assert warmup_weights[1] == 135


def test_custom_bar_weight():
    """Test that custom bar weights are used in calculations."""

    # Use a 35# bar instead of standard 45#
    c = ExerciseCluster(
        week=1,
        exercise="squat",
        oneRepMax=315,
        bar_weight=35.0
    )

    # Should have sets
    assert len(c.sets) > 0

    # First set should use the 35# bar
    first_set = c.sets[0]
    assert first_set.bar_weight == 35.0

    # First set is empty bar set
    assert first_set.weight == 35.0


def test_bar_label_in_exercise_cluster():
    """Test that bar labels are propagated through ExerciseCluster."""

    # Create cluster with bar label
    c = ExerciseCluster(
        week=1,
        exercise="squat",
        oneRepMax=315,
        bar_weight=55.0,
        bar_label="Safety Squat Bar"
    )

    # Should have sets
    assert len(c.sets) > 0

    # First set should use the custom bar weight and label
    first_set = c.sets[0]
    assert first_set.bar_weight == 55.0
    assert first_set.bar_label == "Safety Squat Bar"

    # First set is bar-only, but individual reps should just show "Bar"
    # (label only appears in exercise title)
    assert first_set.weight == 55.0
    assert first_set.plate_breakdown == "Bar"

    # Check that the rendered output shows just "Bar" for individual sets
    output = str(c)
    assert "Bar" in output
    # Label should NOT appear in individual set output
    assert "Safety Squat Bar" not in output


def test_bar_label_without_label():
    """Test that clusters work fine without bar labels (backward compatibility)."""

    c = ExerciseCluster(
        week=1,
        exercise="bench press",
        oneRepMax=255,
        bar_weight=45.0
    )

    # First set should be bar-only without label
    first_set = c.sets[0]
    assert first_set.bar_weight == 45.0
    assert first_set.bar_label is None
    assert first_set.plate_breakdown == "Bar"

    # Check output
    output = str(c)
    assert "Bar" in output
