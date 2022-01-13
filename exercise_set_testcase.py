from exercise_set import ExerciseSet

import unittest

##############
# UNIT TESTS #
##############

class ExerciseSetTestCase(unittest.TestCase):
    def test_init(self):
        pass

    def test_to_str(self):
        pass

    def test_plate_breakdown(self):
        pass

    def test_weight_setter(self):
        pass

    def test_set(self):
        pass
    
    def test_reps(self):
        pass

    def test_calc_lifting_weight(self):
        pass


    def test_calc_weighted_pullup(self):
        pass

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

#############
# RUN TESTS #
#############

if __name__ == '__main__':
    unittest.main()