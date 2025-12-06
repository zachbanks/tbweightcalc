import argparse
import datetime

import tbweightcalc as tb
from tbweightcalc.program import apply_markdown

# Interface: weights.py --squat 400 --bench 200 --deadlift 300 --wpu 245 --bodyweight 190

parser = argparse.ArgumentParser(
    description="Calculates Tactical Barbell weight progression for getting swole."
)

# Define program flags.
parser.add_argument(
    "-t",
    "--title",
    help="Enter title for document. Ex: Tactical Barbell: 2022-01",
    type=str,
)

parser.add_argument(
    "-w",
    "--week",
    help='Enter week to print out for each exercise selected: 1-6 or "all"',
    type=str,
    nargs="?",
    const="all",
)

parser.add_argument("-sq", "--squat", help="Enter 1RM for Squat", type=int)

parser.add_argument("-bp", "--bench", help="Enter 1RM for Bench Press", type=int)

parser.add_argument("-dl", "--deadlift", help="Enter 1RM for Deadlift", type=int)

parser.add_argument(
    "-wpu",
    "--weighted-pullup",
    help='Enter 1RM for Weighted Pull Up followed by bodyweight: "-wpu 245 200"',
    type=int,
    nargs=2,
)

parser.add_argument(
    "--1rm",
    help="Enter weight lifted and number of reps",
    type=int,
    nargs=2,
    dest="onerm",
)


args = parser.parse_args()

# If no arguments are supplied to command line, print help screen.
if not any(vars(args).values()):
    parser.print_help()

# Print exercise if flag is provided.
if args.title:
    print(apply_markdown(f"{args.title}", "h1"))
    print()
    print()
    
WEEK_LABELS = {
    1: "70%",
    2: "80%",
    3: "90%",
    4: "75%",
    5: "85%",
    6: "95%",
}

for i in range(1,7):
    print(apply_markdown(f"WEEK {i} - {WEEK_LABELS[i]}", "h2"))
    print()
    tb.Program.print_exercise(exercise="squat", oneRepMax=args.squat, week=i)
    tb.Program.print_exercise(exercise="bench press", oneRepMax=args.bench, week=i)
    tb.Program.print_exercise(exercise="deadlift", oneRepMax=args.deadlift, week=i)
    tb.Program.print_exercise(
        exercise="weighted pullup",
        oneRepMax=args.weighted_pullup[0],
        body_weight=args.weighted_pullup[1],
        week=i,
    )
    print()
    print(apply_markdown("", "hr"))
    print()

# if args.squat:
#     tb.Program.print_exercise(exercise="squat", oneRepMax=args.squat, week=args.week)
# if args.bench:
#     tb.Program.print_exercise(
#         exercise="bench press", oneRepMax=args.bench, week=args.week
#     )
# if args.deadlift:
#     tb.Program.print_exercise(
#         exercise="deadlift", oneRepMax=args.deadlift, week=args.week
#     )
# if args.weighted_pullup:
#     tb.Program.print_exercise(
#         exercise="weighted pullup",
#         oneRepMax=args.weighted_pullup[0],
#         body_weight=args.weighted_pullup[1],
#         week=args.week,
#     )
# if args.onerm:
#     onerm = tb.Program.calc_1rm(weight=args.onerm[0], reps=args.onerm[1])
#     print(f"One Rep Max: {onerm}")

# Print current date at bottom.
print()
print()
print(datetime.datetime.now().strftime("%x"))
