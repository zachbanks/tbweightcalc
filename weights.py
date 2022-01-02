import argparse

# TODO: Print each of those in markdown table.
# TODO: Correct week 3,5,6 final rep range.

# Takes arg of int value of weight and returns string of plates in format: 400# - (45 x 3) 35 5 2.5
def calculate_warmup_plates(input_weight, bar=True, bar_weight=45):
    # TODO: Weight must be a multiple of 5
    corrected_weight = round_weight(input_weight)
    weight = corrected_weight

    plates = [45,35,25,15,10,5,2.5]
    plate_count = [0] * len(plates) # Initial array with same number of plates in plates array

    if corrected_weight > bar_weight and bar == True:
        weight -= bar_weight # Subtract weight of bar
    weight /= 2 # Only worry about one side of the bar

    while weight > 0:
        for i, v in enumerate(plates):
            while weight >= v:
                plate_count[i] += 1
                weight -= v

    # Create string to return from function
    final_string = ("%d# - " % corrected_weight)

    if bar == True and corrected_weight <= bar_weight:
        final_string += "Bar"
    else:
        for i, v in enumerate(plate_count):
            if v > 1:
                final_string += ("(%s x %d) " % (plates[i], v)) # (45 x 2)
            elif v == 1:
                final_string += ('%s ' % (plates[i]))


    return final_string


# Take working weight for squat and calculate warm up reps for exercise.
# Pass percent as string ie '90%'
# Return dictionary { "2x5": 45, "1x5": 120, "1x3": 150}
def get_reps(exercise, working_weight, percent):
    # 2x5 reps = Bar, multiplier = 0
    # 1x5 reps multiplier = 0.4
    # 1x3 reps multiplier = 0.6
    # 1x2 reps multiplier = 0.8
    # 3x5 reps multiplier = 1.0 (ie working weight)
    working_weight = round_weight(working_weight)

    values = {}

    if exercise == "squat":
        values.update({
            "2x5" : 45,
            "1x5" : round_weight(working_weight * 0.4),
            "1x3" : round_weight(working_weight * 0.6),
            "1x2" : round_weight(working_weight * 0.8),
        })

        final_weight = round_weight(working_weight * 1.0)
        # Week 3
        if percent == "90%":
            values.update({'3-4 x 3': final_weight})
        # Week 5
        elif percent == "85%":
            values.update({'3-5 x 3': final_weight})
        # Week 6
        elif percent == '95%':
            values.update({'3-4 x 1-2': final_weight})
        else:
            values.update({'3-5 x 5': final_weight})

    elif exercise == "bench press":
        # 2x5 reps = Bar, multiplier = 0
        # 1x5 reps multiplier = 0.5
        # 1x3 reps multiplier = 0.7
        # 1x2 reps multiplier = 0.9
        # 3x5 reps multiplier = 1.0 (ie working weight)
        working_weight = round_weight(working_weight)
        values.update({
            "2x5" : 45,
            "1x5" : round_weight(working_weight * 0.5),
            "1x3" : round_weight(working_weight * 0.7),
            "1x2" : round_weight(working_weight * 0.9)
        })

        final_weight = round_weight(working_weight * 1.0)
        # Week 3
        if percent == "90%":
            values.update({'3-4 x 3': final_weight})
        # Week 5
        elif percent == "85%":
            values.update({'3-5 x 3': final_weight})
        # Week 6
        elif percent == '95%':
            values.update({'3-4 x 1-2': final_weight})
        else:
            values.update({'3-5 x 5': final_weight})

    elif exercise == "deadlift":
        # 2x5 reps, multiplier = 0.4
        # 1x3 reps multiplier = 0.6
        # 1x2 reps multiplier = 0.85
        # 1x5 reps multiplier = 1.0 (ie working weight)
        working_weight = round_weight(working_weight)
        values.update({
            "2x5" : round_weight(working_weight * 0.4),
            "1x3" : round_weight(working_weight * 0.6),
            "1x2" : round_weight(working_weight * 0.85)
        })

        final_weight = round_weight(working_weight * 1.0)
        # Week 3
        if percent == "90%":
            values.update({'1-3 x 3': final_weight})
        # Week 5
        elif percent == "85%":
            values.update({'1-3 x 3': final_weight})
        # Week 6
        elif percent == '95%':
            values.update({'1-3 x 1-2': final_weight})
        else:
            values.update({'1-3 x 5': final_weight})

    return values


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
    print('1RM: %s#' % oneRepMax)
    print()

    # Array of dictionaries that contain all the warmup values.
    prog = [{}] * len(weights)
    for i, (percent, value) in enumerate(weights.items()):
        if exercise == "squat":
            prog[i] = get_reps(exercise, value, percent)
        elif exercise == "bench press":
            prog[i] = get_reps(exercise, value, percent)
        elif exercise == "deadlift":
            prog[i] = get_reps(exercise, value, percent)
        print("%s: " % percent) # 70%:

        for x, (reps, weight) in enumerate(prog[i].items()):
            print('%s - %s' % (reps, calculate_warmup_plates(weight)))
        print()


# Program logic

# TODO: Make basic CLI options to change input_weight
# Interface: weights.py --squat 400 --bench 200 --deadlift 300 --wpu 245 --bodyweight 190

parser = argparse.ArgumentParser(description = 'Calculates Tactical Barbell weight progression for getting swole.')

# Define program flags.
parser.add_argument('-sq', '--squat',
    help='Enter 1RM for Squat',
    type=int)

parser.add_argument('-bp', '--bench',
    help='Enter 1RM for Bench Press',
    type=int)

parser.add_argument('-dl', '--deadlift',
    help='Enter 1RM for Deadlift',
    type=int)

parser.add_argument('-wpu', '--weighted-pullup',
    help='Enter 1RM for Weighted Pull Up followed by bodyweight: "-wpu 245 200"',
    type=int,
    nargs=2)


args = parser.parse_args()

# If no arguments are supplied to command line, print help screen.
if not any(vars(args).values()):
    parser.print_help()

# Print exercise if flag is provided.
if args.squat:
    print_exercise("squat", args.squat)
if args.bench:
    print_exercise("bench press", args.bench)
if args.deadlift:
    print_exercise("deadlift", args.deadlift)
if args.weighted_pullup:
    weighted_pullup(args.weighted_pullup[0], args.weighted_pullup[1])
