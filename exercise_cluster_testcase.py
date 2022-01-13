from exercise_cluster import ExerciseCluster

import unittest

from exercise_set import ExerciseSet

##############
# UNIT TESTS #
##############

class ExerciseClusterTestCase(unittest.TestCase):


    def test_str(self):
        # Correctly prints squat output
        c = ExerciseCluster(week = 1, exercise = 'squat', oneRepMax = 400)
        self.assertEqual(str(c), 
        'Week 1: 70%\n2 x 5 - 45# - Bar\n1 x 5 - 110# - 25 5 2.5\n1 x 3 - 170# - 45 15 2.5\n1 x 2 - 225# - (45 x 2)\n(3-5) x 5 - 280# - (45 x 2) 25 2.5\n')

        # Test correct output for bench press.
        c = ExerciseCluster(week = 4, exercise = 'bench press', oneRepMax=230)
        self.assertEqual(str(c), 'Week 4: 75%\n2 x 5 - 45# - Bar\n1 x 5 - 85# - 15 5\n1 x 3 - 120# - 35 2.5\n1 x 2 - 155# - 45 10\n(3-5) x 5 - 170# - 45 15 2.5\n')

        # Tests correct output for deadlift.
        c = ExerciseCluster(week = 3, exercise = 'deadlift', oneRepMax=400)
        self.assertEqual(str(c), 'Week 3: 90%\n2 x 5 - 145# - 45 5\n1 x 3 - 215# - 45 35 5\n1 x 2 - 305# - (45 x 2) 35 5\n(1-3) x 3 - 360# - (45 x 3) 15 5 2.5\n')

        # Weighted pull ups. 
        c = ExerciseCluster(week = 1, exercise='weighted pullup', oneRepMax=240, body_weight=180)
        self.assertEqual(str(c), 'Week 1: 70% - (3-5) x 5 - Bodyweight\n')

        c = ExerciseCluster(week = 3, exercise='weighted pullup', oneRepMax=240, body_weight=180)
        self.assertEqual(str(c), 'Week 3: 90% - (3-4) x 3 - 35#\n')



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
        c = ExerciseCluster(week = 1)
        self.assertEqual(c.label, '70%')

        c = ExerciseCluster(week = 6)
        self.assertEqual(c.label, '95%')


    def test_working_weight(self):
        c = ExerciseCluster(week = 2, oneRepMax=403)
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
        pass



#############
# RUN TESTS #
#############

if __name__ == '__main__':
    unittest.main()