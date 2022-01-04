from exercise_set import ExerciseSet

class ExerciseCluster:

    def __init__(self, week=1, exercise="", oneRepMax = 0, body_weight = None):
        self.week = week # Week 3
        self.exercise = exercise
        self.oneRepMax = oneRepMax
        self.sets = []
        self.body_weight = body_weight

        self.calc_sets()

    def __str__(self):

        s = 'Week %d: %s' % (self.week, self.label)

        if self.exercise == 'weighted pullup':
            s += ' - '
        else:
            s += '\n'

        for i in self.sets:
            s += '%s\n' % str(i)
        return s

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

    def calc_sets(self):
        setreps = []

        if self.exercise == 'squat' or self.exercise == 'bench press' or self.exercise == 'weighted pullup':

            if self.exercise == 'squat' or self.exercise == 'bench press':
                # Squat values
                setreps = [
                    { 'set' : 2, 'reps': 5, 'multiplier': 0 },
                    { 'set' : 1, 'reps': 5, 'multiplier': 0.4 },
                    { 'set' : 1, 'reps': 3, 'multiplier': 0.6 },
                    { 'set' : 1, 'reps': 2, 'multiplier': 0.8 },
                ]

                # If bench, change multiplier values
                if self.exercise == 'bench press':
                    bench_values = [0.0, 0.5, 0.7, 0.9]
                    i = 0
                    for dict in setreps:
                        dict['multiplier'] = bench_values[i]
                        i += 1

            # Change sets and reps for special weeks.
            # 90%
            if self.week == 3:
                setreps.append({
                 'min_set': 3,
                 'max_set': 4,
                 'reps': 3,
                 'range' : True,
                 'multiplier': 1.0 })
            # 85%
            elif self.week == 5:
                setreps.append({
                 'min_set': 3,
                 'max_set': 5,
                 'reps': 3,
                 'range' : True,
                 'multiplier': 1.0 })
            # 95%
            elif self.week == 6:
                setreps.append({
                 'min_set': 3,
                 'max_set': 4,
                 'min_reps': 1,
                 'max_reps': 2,
                 'range' : True,
                 'multiplier': 1.0 })
            # All other weeks.
            else:
                setreps.append({ 'set' : 5, 'reps': 5, 'multiplier': 1.0 })

        elif self.exercise == 'deadlift':

            setreps = [
                { 'set' : 2, 'reps': 5, 'multiplier': 0.4 },
                { 'set' : 1, 'reps': 3, 'multiplier': 0.6 },
                { 'set' : 1, 'reps': 2, 'multiplier': 0.85 }
            ]

            # 90% or 85%
            if self.week == 3 or self.week == 5:
                setreps.append({
                 'min_set': 1,
                 'max_set': 3,
                 'reps': 3,
                 'range' : True,
                 'multiplier': 1.0 })
            # 95%
            elif self.week == 6:
                setreps.append({
                 'min_set': 1,
                 'max_set': 3,
                 'min_reps': 1,
                 'max_reps': 2,
                 'range' : True,
                 'multiplier': 1.0 })
            # All other weeks.
            else:
                setreps.append({ 'set' : 3, 'reps': 5, 'multiplier': 1.0 })

        for dict in setreps:
            s = ExerciseSet()
            # Deal with set and rep ranges
            if 'range' in dict and dict['range'] == True:
                if 'min_set' in dict:
                    s.min_set = dict['min_set']
                if 'max_set' in dict:
                    s.max_set = dict['max_set']
                if 'min_reps' in dict:
                    s.min_reps = dict['min_reps']
                if 'max_reps' in dict:
                    s.max_reps = dict['max_reps']
            else:
                s.set = dict['set']
                s.reps = dict['reps']
            if not self.exercise == 'weighted pullup':
                s.calc_lifting_weight(self.working_weight, dict['multiplier'])
            else:
                s.calc_weighted_pullup(self.working_weight, self.body_weight, dict['multiplier'])

            self.add(s)
