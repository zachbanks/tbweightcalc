from exercise_set import ExerciseSet

class ExerciseCluster:

    def __init__(self, week=1, sets=[], exercise="", oneRepMax = 0):
        self.week = week # Week 3
        self.sets = sets #
        self.exercise = exercise
        self.oneRepMax = oneRepMax

    def __str__(self):
        return str(self.sets)

    # Allows cluster[0] notatoin. Returns ExerciseSet object.
    def __getitem__(self, item):
        return self.sets[item]

    @property
    def week(self):
        return self.__week

    # When week is set, update label, and update week multiplier
    @week.setter
    def week(self, w):
        x = 1.0
        if w == 1:
            x = .70
        elif w == 2:
            x = .80
        elif w == 3:
            x = .90
        elif w == 4:
            x = .75
        elif w == 5:
            x = .85
        elif w == 6:
            x = .95
        # Update week multiplier.
        self.week_multiplier = x
        # Update label.
        self.label = x

        self.__week = int(w) # Must be int.


    @property
    def label(self):
        return self.__label

    @label.setter
    def label(self, l):
        self.__label = '%d%%' % (int(self.week_multiplier * 100)) # 90%

    @property
    def week_multiplier(self):
        return self.__week_multiplier

    @week_multiplier.setter
    def week_multiplier(self, m):
        self.__week_multiplier = m

    @property
    def working_weight(self):
        return ExerciseSet.round_weight(self.oneRepMax * self.week_multiplier)

    # Adds ExerciseSet object to cluster.
    def add(self, set):
        self.sets.append(set)
