class ExerciseSet:

    bar_weight = 45

    def __init__(self, min_set=None, max_set=5, min_reps=None, max_reps=5, weight = 0, bar = True):
        self.min_set = min_set
        self.max_set = max_set
        self.min_reps = min_reps
        self.max_reps = max_reps
        self.weight = weight
        self.bar = bar

    def __str__(self):
        str, set, rep = '', '', ''

        # Format sets.
        # 3x5
        if self.min_set == None:
            set = '%d' % (self.set) # 3
        # (3-5) x 5
        elif self.min_set >= 0 and self.max_set > 0:
            set = '(%d-%d)' % (self.min_set, self.max_set)

        # Format reps
        # Single digit reps only ie 3x5
        if self.min_reps == None:
            rep = '%d' % (self.reps)
        elif self.min_reps >= 0 and self.max_reps > 0:
            rep = '(%d-%d)' % (self.min_reps, self.max_reps)

        # Combine set and rep strings
        str = '%s x %s' % (set, rep) # 3x5 or (3-4)x(1-2)
        str += ' - %d#' % (self.weight)

        # Add plate breakdown
        str += ' - %s' % self.plate_breakdown

        return str

    @property
    def plate_breakdown(self):
        return self.__plate_breakdown

    @plate_breakdown.setter
    def plate_breakdown(self, s):
        self.__plate_breakdown = s

    @property
    def weight(self):
        return self.__weight

    @weight.setter
    def weight(self, w):
        self.__plate_breakdown = ExerciseSet.calc_plate_breakdown(w)
        self.__weight = w

    @property
    def set(self):
        return self.max_set

    @set.setter
    def set(self, s):
        self.max_set = s

    @property
    def reps(self):
        return self.max_reps

    @reps.setter
    def reps(self, r):
        self.max_reps = r

    def calc_lifting_weight(self, working_weight, multiplier):
        w = ExerciseSet.round_weight(working_weight * multiplier)

        if w == 0:
            self.weight = ExerciseSet.bar_weight
        else:
            self.weight = w

    # Takes arg of int value of weight and returns string of plates in format: 400# - (45 x 3) 35 5 2.5
    @classmethod
    def calc_plate_breakdown(cls, input_weight=0, bar=True):
        corrected_weight = ExerciseSet.round_weight(input_weight)
        weight = corrected_weight

        plates = [45,35,25,15,10,5,2.5]
        plate_count = [0] * len(plates) # Initial array with same number of plates in plates array

        if corrected_weight > cls.bar_weight and bar == True:
            weight -= cls.bar_weight # Subtract weight of bar
        weight /= 2 # Only worry about one side of the bar


        while weight > 0:
            for i, v in enumerate(plates):
                while weight >= v:
                    plate_count[i] += 1
                    weight -= v

        # Create string to return from function
        final_string = ''

        if bar == True and corrected_weight <= cls.bar_weight:
            final_string += "Bar"
        else:
            for i, v in enumerate(plate_count):
                if v > 1:
                    final_string += ("(%s x %d) " % (plates[i], v)) # (45 x 2)
                elif v == 1:
                    final_string += ('%s ' % (plates[i]))

        return final_string

    # Round weight down to nearest multiple of 5
    @staticmethod
    def round_weight(weight):
        return int(5 * round(weight/5))
