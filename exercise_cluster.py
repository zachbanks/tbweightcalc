class ExerciseCluster:

    def __init__(self, label="", multiplier=1.0, week=0, sets=[], exercise="") :
        self.label = label # 90%
        self.multiplier = multiplier
        self.week = week # Week 3
        self.sets = sets #
        self.exercise = exercise

    def __str__(self):
        return str(self.sets)

    # Allows cluster[0] notatoin. Returns ExerciseSet object.
    def __getitem__(self, item):
        return self.sets[item]

    # Adds ExerciseSet object to cluster.
    def add(self, set):
        self.sets.append(set)
