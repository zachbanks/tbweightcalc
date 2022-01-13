from exercise_cluster import ExerciseCluster

import unittest

##############
# UNIT TESTS #
##############

class ExerciseClusterTestCase(unittest.TestCase):


    def test_str(self):
        pass


    def test_get_item(self):
        # If cluster[0] or cluster[1]
        # Should proper return exercise set item
        c = ExerciseCluster(exercise='squat', oneRepMax=425)
        self.assertEqual(str(c[0]), '2 x 5 - 45# - Bar') # First set
        self.assertEqual(str(c[-1]), '(3-5) x 5 - 300# - (45 x 2) 35 2.5') # Last set


    def test_week_setter(self):
        # When week is set, label and multiplier should update
        c = ExerciseCluster(exercise='squat', oneRepMax=425, week = 1)
        self.assertEqual(c.week, 1)
        self.assertEqual(c.week_multiplier, 0.70)
        self.assertEqual(c.label, '70%')

        c.week = 2
        self.assertEqual(c.week, 2)
        self.assertEqual(c.week_multiplier, 0.80)
        self.assertEqual(c.label, '80%')

        c.week = 3
        self.assertEqual(c.week, 3)
        self.assertEqual(c.week_multiplier, 0.90)
        self.assertEqual(c.label, '90%')

        c.week = 4
        self.assertEqual(c.week, 4)
        self.assertEqual(c.week_multiplier, 0.75)
        self.assertEqual(c.label, '75%')

        c.week = 5
        self.assertEqual(c.week, 5)
        self.assertEqual(c.week_multiplier, 0.85)
        self.assertEqual(c.label, '85%')

        c.week = 6
        self.assertEqual(c.week, 6)
        self.assertEqual(c.week_multiplier, 0.95)
        self.assertEqual(c.label, '95%')

        # Week 7+ currently not defined, should return week 1
        c.week = 7
        self.assertEqual(c.week, 1)
        self.assertEqual(c.week_multiplier, 0.70)
        self.assertEqual(c.label, '70%')  



    def test_label(self):
        pass


    def test_working_weight(self):
        pass


    def test_add(self):
        pass


    def test_calc_sets(self):
        pass



#############
# RUN TESTS #
#############

if __name__ == '__main__':
    unittest.main()