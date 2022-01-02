# TODO: Print each of those in markdown table.

# Takes arg of int value of weight and returns string of plates in format: 400# - (45 x 3) 35 5 2.5
def calculate_warmup_plates(input_weight, bar=True):
    # TODO: Weight must be a multiple of 5
    corrected_weight = round_weight(input_weight)
    weight = corrected_weight

    plates = [45,35,25,15,10,5,2.5]
    plate_count = [0] * len(plates) # Initial array with same number of plates in plates array

    if corrected_weight > 45 and bar == True:
        weight -= 45 # Subtract weight of bar
    weight /= 2 # Only worry about one side of the bar

    while weight > 0:
        for i, v in enumerate(plates):
            while weight >= v:
                plate_count[i] += 1
                weight -= v

    # Create string to return from function
    final_string = ("%d# - " % corrected_weight)

    if bar == True and corrected_weight <= 45:
        final_string += "Bar"
    else:
        for i, v in enumerate(plate_count):
            if v > 1:
                final_string += ("(%s x %d) " % (plates[i], v)) # (45 x 2)
            elif v == 1:
                final_string += ('%s ' % (plates[i]))


    return final_string


# Take working weight for squat and calculate warm up reps for exercise.
# Return dictionary? { "2x5": 45, "1x5": 120, "1x3": 150}
def squat_reps(working_weight):
    # 2x5 reps = Bar, multiplier = 0
    # 1x5 reps multiplier = 0.4
    # 1x3 reps multiplier = 0.6
    # 1x2 reps multiplier = 0.8
    # 3x5 reps multiplier = 1.0 (ie working weight)
    working_weight = round_weight(working_weight)
    return {
        "2x5" : 45,
        "1x5" : round_weight(working_weight * 0.4),
        "1x3" : round_weight(working_weight * 0.6),
        "1x2" : round_weight(working_weight * 0.8),
        "3x5" : round_weight(working_weight * 1.0)
    }


def bench_reps(working_weight):
    # 2x5 reps = Bar, multiplier = 0
    # 1x5 reps multiplier = 0.5
    # 1x3 reps multiplier = 0.7
    # 1x2 reps multiplier = 0.9
    # 3x5 reps multiplier = 1.0 (ie working weight)
    working_weight = round_weight(working_weight)
    return {
        "2x5" : 45,
        "1x5" : round_weight(working_weight * 0.5),
        "1x3" : round_weight(working_weight * 0.7),
        "1x2" : round_weight(working_weight * 0.9),
        "3x5" : round_weight(working_weight * 1.0)
    }


def deadlift_reps(working_weight):
    # 2x5 reps, multiplier = 0.4
    # 1x3 reps multiplier = 0.6
    # 1x2 reps multiplier = 0.85
    # 1x5 reps multiplier = 1.0 (ie working weight)
    return {
        "2x5" : round_weight(working_weight * 0.4),
        "1x3" : round_weight(working_weight * 0.6),
        "1x2" : round_weight(working_weight * 0.85),
        "1x5" : round_weight(working_weight * 1.0)
    }

# Print progression of WPU. oneRep Max is calculated 1RM with body weight included.
def weighted_pullup(oneRepMax, body_weight):
    multipliers = [.70,.75,.80,.85,.90,.95]
    values = {
        '70%' : '0',
        '75%': '0',
        '80%': '0',
        '85%': '0',
        '90%': '0',
        '95%': '0',
    }

    for i, (set, weight) in enumerate(values.items()):
        calc_weight = (oneRepMax * multipliers[i]) - body_weight

        if calc_weight <= 0:
            values[set] = "Bodyweight"
        else:
            values[set] = str(calculate_warmup_plates(round_weight(calc_weight), False))

    print(" ### Weighted Pull Ups @ %d# ###" % body_weight)
    print()

    # TODO: Figure out why it keeps printing None at end of this string. Prob something to do with iteration of dictionary.

    for set, weight in values.items():
        print('(3-5 x 5) @ %s | %s' %(set, weight))


# Calculate the weight progressions of 70, 75, 80, 85, 90, 95 given the
# input of the one rep max
# Returns dictionary
def calc_weight_progression(oneRepMax):
    return {
        "70%" : round_weight(oneRepMax * .70),
        "75%" : round_weight(oneRepMax * .75),
        "80%" : round_weight(oneRepMax * .80),
        "85%" : round_weight(oneRepMax * .85),
        "90%" : round_weight(oneRepMax * .90),
        "95%" : round_weight(oneRepMax * .95),
    }

# Round weight down to nearest multiple of 5
def round_weight(weight):
    return int(5 * round(weight/5))

def print_exercise(exercise, oneRepMax):
    weights = calc_weight_progression(oneRepMax)

    print("##### %s #####" % (exercise.upper()))
    print()

    # Array of dictionaries that contain all the warmup values.
    prog = [{}] * len(weights)
    for i, (percent, value) in enumerate(weights.items()):
        if exercise == "squat":
            prog[i] = squat_reps(value)
        elif exercise == "bench press":
            prog[i] = bench_reps(value)
        elif exercise == "deadlift":
            prog[i] = deadlift_reps(value)
        print("%s: " % percent) # 70%:

        for x, (reps, weight) in enumerate(prog[i].items()):
            print('%s - %s' % (reps, calculate_warmup_plates(weight)))
        print()


# Program logic

print_exercise("squat", 400)
print_exercise("bench press", 230)
print_exercise("deadlift", 325)


weighted_pullup(255, 200)
