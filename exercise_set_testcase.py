from exercise_set import ExerciseSet

import unittest

##############
# UNIT TESTS #
##############

class ExerciseSetTestCase(unittest.TestCase):

    def test_to_str(self):
        # Returns correctly formatted set string.

        # Tests default max sets and reps to 5x5
        s = ExerciseSet(weight = 425)
        self.assertEqual(str(s), '5 x 5 - 425# - (45 x 4) 10')

        # Tests different min and max sets / reps
        s = ExerciseSet(weight = 425, min_set=3, min_reps=3)
        self.assertEqual(str(s), '(3-5) x (3-5) - 425# - (45 x 4) 10')

        s = ExerciseSet(weight = 425, min_set=1, max_set=10, min_reps=3, max_reps=15)
        self.assertEqual(str(s), '(1-10) x (3-15) - 425# - (45 x 4) 10')

        # Test default
        s = ExerciseSet()
        self.assertEqual(str(s), '5 x 5 - 0# - Bar')


    def test_weight_setter(self):
        # Updates plate breakdown when weight is set.
        s = ExerciseSet(weight = 300)
        self.assertEqual(s.plate_breakdown, '(45 x 2) 35 2.5')

        # Change weight, should update.
        s.weight = 500
        self.assertEqual(s.plate_breakdown, '(45 x 5) 2.5')


    def test_set(self):
        # Should return max sets
        s = ExerciseSet(max_set=8)
        self.assertEqual(s.set, 8)


    def test_reps(self):
        # reps should return max reps
        s = ExerciseSet(max_reps=10)
        self.assertEqual(s.reps, 10)


    def test_calc_lifting_weight(self):
        s = ExerciseSet()

        # Check weight gets rounded.
        s.calc_lifting_weight(133, 1.0)
        self.assertEqual(s.weight, 135)

        # If weight is 0, set to barweight
        s.calc_lifting_weight(0, 1.0)
        self.assertEqual(s.weight, ExerciseSet.bar_weight)

        # If weight is 45, set to barweight (default is 45)
        s.calc_lifting_weight(45, 1.0)
        self.assertEqual(s.weight, ExerciseSet.bar_weight)

        # Properly calculates lifting weight * multiplier
        s.calc_lifting_weight(225, 0.85)
        self.assertEqual(s.weight, 190)

        s.calc_lifting_weight(225, 0.55)
        self.assertEqual(s.weight, 125)


    def test_calc_weighted_pullup(self):
        s = ExerciseSet()

        # Weight should = working weight * multiplier - bodyweight
        s.calc_weighted_pullup(260, 200, 1.0)
        self.assertEqual(s.weight, 60)
        self.assertEqual(s.plate_breakdown, '25 5')

        s.calc_weighted_pullup(260, 200, 0.90)
        self.assertEqual(s.weight, 34)
        self.assertEqual(s.plate_breakdown, '15 2.5')

        # If weight returns negative => 0
        s.calc_weighted_pullup(260, 200, 0.75)
        self.assertEqual(s.weight, 0)
        self.assertEqual(s.plate_breakdown, 'Bodyweight')


    def test_calc_platebreakdown(self):
        # Rounds weight and returns proper breakdown
        self.assertEqual(ExerciseSet.calc_plate_breakdown(400), '(45 x 3) 35 5 2.5')
        self.assertEqual(ExerciseSet.calc_plate_breakdown(135), '45')
        self.assertEqual(ExerciseSet.calc_plate_breakdown(150), '45 5 2.5')
        
        # If weight <= 45, return 'Bar'
        self.assertEqual(ExerciseSet.calc_plate_breakdown(45), 'Bar')
        self.assertEqual(ExerciseSet.calc_plate_breakdown(-1, bar = True), 'Bar')

        # Breakdown plate breakdown if bar == False and weight less 45
        self.assertEqual(ExerciseSet.calc_plate_breakdown(45, bar = False), '15 5 2.5')
        self.assertEqual(ExerciseSet.calc_plate_breakdown(25, bar = False), '10 2.5')

        # Return bodyweight if weight <= 0 and bar == False
        self.assertEqual(ExerciseSet.calc_plate_breakdown(-1, bar = False), 'Bodyweight')
        self.assertEqual(ExerciseSet.calc_plate_breakdown(0, bar = False), 'Bodyweight')


    def test_round_weight(self):
        # Rounds to nearest increment of 5
        self.assertEqual(ExerciseSet.round_weight(8), 10, "8 => 10")
        self.assertEqual(ExerciseSet.round_weight(6), 5, "6 => 5")
        self.assertEqual(ExerciseSet.round_weight(1), 0, "1 => 0")
        self.assertEqual(ExerciseSet.round_weight(4), 5, "4 => 5")
        self.assertEqual(ExerciseSet.round_weight(-1), 0, "-1 => 0")
        self.assertEqual(ExerciseSet.round_weight(257), 255, "257 => 255")
        self.assertEqual(ExerciseSet.round_weight(343.23), 345)

#############
# RUN TESTS #
#############

if __name__ == '__main__':
    unittest.main()