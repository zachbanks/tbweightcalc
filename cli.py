import argparse
import datetime

import tbweightcalc as tb
from tbweightcalc.program import apply_markdown
from tbweightcalc.program import markdown_to_pdf

# Interface: weights.py --squat 400 --bench 200 --deadlift 300 --wpu 245 --bodyweight 190

parser = argparse.ArgumentParser(
    description="Calculates Tactical Barbell weight progression for getting swole."
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

parser.add_argument(
    "--pdf",
    metavar="PATH",
    help="Write output to a PDF at PATH instead of printing markdown",
)

parser.add_argument(
    "--title",
    help="Optional title for the program/PDF; if omitted, a default title is used",
)


args = parser.parse_args()

# If no arguments are supplied to command line, print help screen.
if not any(vars(args).values()):
    parser.print_help()

if args.title:
    title = args.title
else:
    title = f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"

WEEK_LABELS = {
    1: "70%",
    2: "80%",
    3: "90%",
    4: "75%",
    5: "85%",
    6: "95%",
}

def build_program_markdown(args, for_pdf: bool = False) -> str:
    """
    Build the Tactical Barbell program markdown.

    for_pdf=False:
        - includes visible '---' horizontal rules between weeks
    for_pdf=True:
        - uses raw '\\newpage' between weeks (no HR printed in PDF)
    """
    lines: list[str] = []

    for week in range(1, 7):
        # WEEK header
        lines.append(apply_markdown(f"WEEK {week} - {WEEK_LABELS[week]}", "h2"))
        lines.append("")

        # Squat
        lines.append(
            tb.Program.print_exercise(
                exercise="squat",
                oneRepMax=args.squat,
                week=week,
                body_weight=None,
                print_1rm=True,
            )
        )
        lines.append("")

        # Bench
        lines.append(
            tb.Program.print_exercise(
                exercise="bench press",
                oneRepMax=args.bench,
                week=week,
                body_weight=None,
                print_1rm=True,
            )
        )
        lines.append("")

        # Deadlift
        lines.append(
            tb.Program.print_exercise(
                exercise="deadlift",
                oneRepMax=args.deadlift,
                week=week,
                body_weight=None,
                print_1rm=True,
            )
        )
        lines.append("")

        # Weighted pull-up
        lines.append(
            tb.Program.print_exercise(
                exercise="weighted pullup",
                oneRepMax=args.weighted_pullup[0],
                body_weight=args.weighted_pullup[1],
                week=week,
                print_1rm=True,
            )
        )

        # Between weeks: HR or page break
        if week != 6:  # no separator after last week
            if for_pdf:
                # Page break only, no visible HR
                lines.append(r"\pagebreak")
            else:
                # Visible horizontal rule in terminal markdown
                lines.append("")
                # lines.append(apply_markdown("", "hr"))
                lines.append("")

    return "\n".join(lines).rstrip()  # strip trailing blank lines

if __name__ == "__main__":
    args = parser.parse_args()

    # Decide title
    if args.title:
        title = args.title
    else:
        title = f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"

    if args.pdf:
        # Build PDF-specific markdown (with \newpage instead of HR)
        body_markdown = build_program_markdown(args, for_pdf=True)
        markdown_to_pdf(body_markdown, args.pdf, title=title)
    else:
        # Build terminal/markdown output (with visible ---)
        body_markdown = build_program_markdown(args, for_pdf=False)
        print(f"# {title}\n")
        print(body_markdown)

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

