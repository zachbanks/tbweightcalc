class ExerciseCluster:

    def __init__(self, week_multiplier=0.7, week=0, sets=[], exercise="", working_weight = 0):
        self.week_multiplier = week_multiplier # .70
        self.label = '%d%%' % (int(week_multiplier * 100)) # 90%
        self.week = week # Week 3
        self.sets = sets #
        self.exercise = exercise
        self.working_weight = working_weight

    def __str__(self):
        return str(self.sets)

    # Allows cluster[0] notatoin. Returns ExerciseSet object.
    def __getitem__(self, item):
        return self.sets[item]

    # Adds ExerciseSet object to cluster.
    def add(self, set):
        self.sets.append(set)
