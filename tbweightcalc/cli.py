from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import tbweightcalc as tb
from tbweightcalc.formatting import Formatter, MarkdownFormatter, PlainFormatter
from tbweightcalc.onerm import calculate_one_rm
from tbweightcalc.program import markdown_to_pdf


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
# Which exercises are available for interactive mode, grouped into logical “slots”

def format_exercise_name(exercise_name: str) -> str:
    """
    Format exercise name for display with proper capitalization.

    Special cases:
    - "rdl" -> "RDL"
    - others -> Title Case
    """
    if exercise_name.lower() == "rdl":
        return "RDL"
    return exercise_name.title()


INTERACTIVE_LIFT_SLOTS = [
    {
        "name": "Lower-body main lift",
        "options": [
            {
                "key": "squat",
                "exercise_name": "squat",
                "prompt": "Squat 1RM or set (e.g. '455' or '240 5' or '240x5', blank to skip): ",
            },
            {
                "key": "front_squat",
                "exercise_name": "front squat",
                "prompt": "Front squat 1RM or set (e.g. '355' or '185 5' or '185x5', blank to skip): ",
            },
            {
                "key": "zercher_squat",
                "exercise_name": "zercher squat",
                "prompt": "Zercher squat 1RM or set (e.g. '315' or '225 5' or '225x5', blank to skip): ",
            },
        ],
    },
    {
        "name": "Upper-body main press",
        "options": [
            {
                "key": "bench",
                "exercise_name": "bench press",
                "prompt": "Bench press 1RM or set (e.g. '315' or '225 5' or '225x5', blank to skip): ",
            },
            {
                "key": "overhead_press",
                "exercise_name": "overhead press",
                "prompt": "Overhead press 1RM or set (e.g. '185' or '135 5' or '135x5', blank to skip): ",
            },
        ],
    },
    {
        "name": "Hinge",
        "options": [
            {
                "key": "deadlift",
                "exercise_name": "deadlift",
                "prompt": "Deadlift 1RM or set (e.g. '455' or '315 5' or '315x5', blank to skip): ",
            },
            {
                "key": "zercher_deadlift",
                "exercise_name": "zercher deadlift",
                "prompt": "Zercher deadlift 1RM or set (e.g. '405' or '275 5' or '275x5', blank to skip): ",
            },
            {
                "key": "trap_bar_deadlift",
                "exercise_name": "trap bar deadlift",
                "prompt": "Trap bar deadlift 1RM or set (e.g. '500' or '365 5' or '365x5', blank to skip): ",
            },
            {
                "key": "rdl",
                "exercise_name": "rdl",
                "prompt": "RDL 1RM or set (e.g. '365' or '275 5' or '275x5', blank to skip): ",
            },
        ],
    },
    # Weighted pull-up is handled separately because of bodyweight.
]


def _prompt_for_exercise_1rm(exercise_name: str) -> tuple[int | None, float]:
    """
    Look up the interactive prompt text for the given exercise_name
    from INTERACTIVE_LIFT_SLOTS and run prompt_lift_one_rm on it.

    Returns (1RM, bar_weight) where 1RM can be None if skipped.
    """
    for slot in INTERACTIVE_LIFT_SLOTS:
        for opt in slot["options"]:
            if opt["exercise_name"] == exercise_name:
                one_rm = prompt_lift_one_rm(opt["prompt"])
                if one_rm is None:
                    return (None, 45.0)
                bar_weight = prompt_bar_weight(exercise_name)
                return (one_rm, bar_weight)
    # If not found in config, just fall back to a generic prompt.
    generic = f"{format_exercise_name(exercise_name)} 1RM or set (e.g. '225', '200 5', '200x5', blank to skip): "
    one_rm = prompt_lift_one_rm(generic)
    if one_rm is None:
        return (None, 45.0)
    bar_weight = prompt_bar_weight(exercise_name)
    return (one_rm, bar_weight)


def copy_to_clipboard(text: str) -> None:
    """
    Copy text to system clipboard if a clipboard tool is available.

    On macOS, this uses pbcopy. If pbcopy is not available (e.g. in Docker),
    this silently does nothing.
    """
    pbcopy = shutil.which("pbcopy")
    if not pbcopy:
        return

    try:
        subprocess.run(
            [pbcopy],
            input=text.encode("utf-8"),
            check=True,
        )
    except Exception:
        # Don't crash if clipboard fails
        pass


def default_pdf_path(title: Optional[str]) -> Path:
    """
    Default PDF location: ~/Downloads/<title>.pdf

    If title is None, use a dated default.
    """
    if not title:
        title = f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"

    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", title).strip("_")
    if not safe.lower().endswith(".pdf"):
        safe = safe + ".pdf"

    downloads = Path.home() / "Downloads"
    return downloads / safe


def build_program_markdown(
    args: argparse.Namespace,
    for_pdf: bool = False,
    formatter: Formatter | None = None,
) -> str:
    """
    Build the Tactical Barbell program markdown.

    - If args.lifts is present, it is a dict:
        { "squat": {"one_rm": 455, "body_weight": None}, ... }
      and we render based on that.
    - Otherwise, we fall back to the legacy fixed fields:
        args.squat, args.bench, args.deadlift, args.weighted_pullup, etc.
    """
    fmt = formatter
    if fmt is None:
        fmt = MarkdownFormatter() if for_pdf else PlainFormatter()

    lines: list[str] = []

    week_percentages = {
        1: "70%",
        2: "80%",
        3: "90%",
        4: "75%",
        5: "85%",
        6: "95%",
    }

    # Decide which weeks to print
    if getattr(args, "week", None) and args.week != "all":
        weeks = [int(args.week)]
    else:
        weeks = list(range(1, 7))

    # ----- Build a unified lifts dict -----
    if hasattr(args, "lifts") and args.lifts:
        lifts = args.lifts  # from interactive mode
    else:
        # Legacy path — build from old fields for CLI flags.
        lifts: dict[str, dict] = {}
        if getattr(args, "squat", None) is not None:
            lifts["squat"] = {"one_rm": round(args.squat), "body_weight": None, "bar_weight": 45.0}
        if getattr(args, "front_squat", None) is not None:
            lifts["front squat"] = {"one_rm": round(args.front_squat), "body_weight": None, "bar_weight": 45.0}
        if getattr(args, "zercher_squat", None) is not None:
            lifts["zercher squat"] = {"one_rm": round(args.zercher_squat), "body_weight": None, "bar_weight": 45.0}
        if getattr(args, "bench", None) is not None:
            lifts["bench press"] = {"one_rm": round(args.bench), "body_weight": None, "bar_weight": 45.0}
        if getattr(args, "overhead_press", None) is not None:
            lifts["overhead press"] = {
                "one_rm": round(args.overhead_press),
                "body_weight": None,
                "bar_weight": 45.0,
            }
        if getattr(args, "deadlift", None) is not None:
            lifts["deadlift"] = {"one_rm": round(args.deadlift), "body_weight": None, "bar_weight": 45.0}
        if getattr(args, "zercher_deadlift", None) is not None:
            lifts["zercher deadlift"] = {"one_rm": round(args.zercher_deadlift), "body_weight": None, "bar_weight": 45.0}
        if getattr(args, "trap_bar_deadlift", None) is not None:
            lifts["trap bar deadlift"] = {"one_rm": round(args.trap_bar_deadlift), "body_weight": None, "bar_weight": 45.0}
        wpu = getattr(args, "weighted_pullup", None)
        if wpu is not None:
            one_rm, bw = wpu
            lifts["weighted pullup"] = {"one_rm": one_rm, "body_weight": bw, "bar_weight": 45.0}

    # Define the order in which lifts appear in the output.
    # Extend this list in the future as you add new exercise types.
    print_order = [
        "squat",
        "front squat",
        "zercher squat",
        "bench press",
        "overhead press",
        "deadlift",
        "zercher deadlift",
        "trap bar deadlift",
        "weighted pullup",
    ]

    # Add any extra exercises that aren't in the standard print_order
    for ex_name in lifts:
        if ex_name not in print_order:
            print_order.append(ex_name)

    for week in weeks:
        lines.append(fmt.heading(f"WEEK {week} - {week_percentages[week]}", level=2))
        lines.append("")

        for ex_name in print_order:
            if ex_name not in lifts:
                continue
            cfg = lifts[ex_name]
            one_rm = cfg["one_rm"]
            body_weight = cfg.get("body_weight")
            bar_weight = cfg.get("bar_weight", 45.0)

            lines.append(
                tb.Program.print_exercise(
                    exercise=ex_name,
                    oneRepMax=one_rm,
                    body_weight=body_weight,
                    bar_weight=bar_weight,
                    formatter=fmt,
                    week=week,
                    print_1rm=True,
                )
            )
            lines.append("")

        # Separator between weeks (only if multiple weeks)
        if week != weeks[-1]:
            if for_pdf:
                lines.append(r"\pagebreak")
            else:
                lines.append("")
                lines.append(fmt.horizontal_rule())
                lines.append("")

    return "\n".join(lines).rstrip()


# -------------------------------------------------------------------
# 1RM parsing helpers
# -------------------------------------------------------------------


def parse_one_rm_string(raw: str) -> int | None:
    """
    Parse generic 1RM input string.

    Accepts:
      - '' or whitespace        -> None
      - '455' or '255.6'        -> 455 or 256 (rounded to nearest int)
      - '240 5' or '240.5 5'    -> estimate 1RM from weight x reps (rounded)
      - '240x5', '240 x5',
        '240x 5', '240 x 5'     -> same as above
    """
    raw = raw.strip()
    if not raw:
        return None

    # '240x5' / '240.5x5' / '240 x5' / '240x 5' / '240 x 5'
    m = re.match(r"^(\d+(?:\.\d+)?)\s*[xX]\s*(\d+)$", raw)
    if m:
        weight = float(m.group(1))
        reps = int(m.group(2))
        return calculate_one_rm(weight, reps)

    parts = raw.split()

    # '240 5' or '240.5 5'
    if len(parts) == 2:
        try:
            weight = float(parts[0])
            reps = int(parts[1])
            return calculate_one_rm(weight, reps)
        except ValueError:
            return None

    # Single number '455' or '255.6' -> literal 1RM (rounded)
    if len(parts) == 1:
        try:
            return round(float(parts[0]))
        except ValueError:
            return None

    return None


def parse_weighted_pullup_string(bodyweight: int, raw: str) -> int | None:
    """
    Parse weighted pull-up input given a bodyweight.

    bodyweight: integer body weight in lb.

    raw: one of:
      - '' or whitespace                -> returns None
      - '35 4' or '35.5 4'              -> +35 or +35.5 lb for 4 reps
      - '35x4', '35 x4',
        '35x 4', '35 x 4'               -> +35 lb for 4 reps
      - '0 4'                           -> bodyweight-only for 4 reps
      - 'bw'                            -> bodyweight-only for 1 rep
      - 'bwx4', 'bw x4', 'bw x 4',
        'bw 4'                          -> bodyweight-only for 4 reps
      - '45' or '45.5'                  -> +45 or +45.5 lb for 1 rep

    Returns:
      - total 1RM (bodyweight + added) as an int (rounded)
      - None if input is blank or invalid
    """
    raw = raw.strip()
    if not raw:
        return None

    lower = raw.lower()

    added: float
    reps: int

    # --- BW-only shorthands ---
    if lower == "bw":
        added = 0
        reps = 1
    else:
        # "bwx4", "bw x4", "bw x 4", "bw 4"
        m_bw = re.match(r"^bw\s*[xX]?\s*(\d+)$", lower)
        if m_bw:
            added = 0
            reps = int(m_bw.group(1))
        else:
            # --- Numeric styles ---

            # '35x4', '35.5x4', '35 x4', '35x 4', '35 x 4'
            m = re.match(r"^(\d+(?:\.\d+)?)\s*[xX]\s*(\d+)$", raw)
            if m:
                added = float(m.group(1))
                reps = int(m.group(2))
            else:
                parts = raw.split()

                # '35 4' or '35.5 4' style
                if len(parts) == 2:
                    try:
                        added = float(parts[0])
                        reps = int(parts[1])
                    except ValueError:
                        return None

                # Single number '45' or '45.5' -> +45 lb for 1 rep
                elif len(parts) == 1:
                    try:
                        added = float(parts[0])
                        reps = 1
                    except ValueError:
                        return None
                else:
                    return None

    total_weight = bodyweight + added
    return calculate_one_rm(total_weight, reps)


# -------------------------------------------------------------------
# Interactive helpers
# -------------------------------------------------------------------


def prompt_bar_weight(exercise_name: str) -> float:
    """
    Prompt for bar weight with default of 45 pounds.

    Returns:
      - float bar weight (defaults to 45.0)
    """
    while True:
        raw = input(f"Bar weight for {exercise_name} (default 45): ").strip()

        # Default to 45
        if not raw:
            return 45.0

        try:
            bar_weight = float(raw)
            if bar_weight > 0:
                return bar_weight
            else:
                print("Bar weight must be greater than 0. Try again or press Enter for default (45).")
        except ValueError:
            print("Invalid input. Enter a number or press Enter for default (45).")


def prompt_lift_one_rm(label: str) -> int | None:
    """
    Prompt for a lift 1RM or set using parse_one_rm_string.

    Loops until:
      - user enters a valid 1RM/set string -> returns int
      - user enters blank                  -> returns None
    """
    while True:
        raw = input(
            f"{label} 1RM or set (e.g. '455' or '240 5' or '240x5', blank to skip): "
        )
        stripped = raw.strip()

        # User decided to skip this lift
        if not stripped:
            return None

        value = parse_one_rm_string(stripped)
        if value is not None:
            return value

        print(
            f"Could not parse input for {label!r}. "
            "Please try again, or leave blank to skip."
        )


def prompt_weighted_pullup_interactive() -> tuple[int | None, int | None]:
    """
    Interactive prompt for weighted pull-ups.

    - Asks for bodyweight (loops until valid int or blank)
    - If bodyweight given:
        Asks for WPU set using parse_weighted_pullup_string(), loops
        until valid, blank, or skip.

    Returns:
      (one_rep_max_total, bodyweight)

    Where:
      - one_rep_max_total can be None if user skips WPU
      - bodyweight can be None if user skips entirely
    """

    # --- Bodyweight prompt (loop until valid or blank) ---
    bodyweight: int | None = None
    while True:
        bw_raw = input(
            "Bodyweight for weighted pull-ups (lb, blank to skip WPU): "
        ).strip()

        if not bw_raw:
            # User skipped WPU entirely
            return None, None

        try:
            bodyweight = int(bw_raw)
            break
        except ValueError:
            print(
                "Invalid bodyweight. Please enter a whole number or leave blank to skip."
            )

    # --- WPU set prompt (loop until valid or blank) ---
    while True:
        wpu_raw = input(
            "Weighted pull-up set (additional weight and reps). Examples:\n"
            "  '35 4'   -> +35 lb for 4 reps\n"
            "  '35x4'   -> +35 lb for 4 reps\n"
            "  '45'     -> +45 lb for 1 rep\n"
            "  '0 4'    -> bodyweight-only for 4 reps\n"
            "  'bw 4'   -> bodyweight-only for 4 reps\n"
            "  'bwx4'   -> bodyweight-only for 4 reps\n"
            "Blank to skip WPU: "
        )

        stripped = wpu_raw.strip()
        if not stripped:
            # No WPU performance entered, but we know bodyweight
            return None, bodyweight

        one_rm = parse_weighted_pullup_string(bodyweight, stripped)
        if one_rm is not None:
            return one_rm, bodyweight

        print(
            "Could not parse weighted pull-up input. "
            "Please try again, or leave blank to skip."
        )


def prompt_one_rm() -> None:
    """
    Simple interactive 1RM prompt:

    - Asks for weight (lbs)
    - Asks for reps
    - Prints estimated 1RM (rounded to nearest lb)
    - Copies *number only* to clipboard
    """
    print("=== 1RM Estimator (Epley) ===")
    try:
        raw_weight = input("Enter weight lifted (in pounds): ").strip()
        raw_reps = input("Enter number of reps: ").strip()

        weight = float(raw_weight)
        reps = int(raw_reps)

        est = calculate_one_rm(weight, reps)
        print(f"\nEstimated 1RM: {est} lb")
        copy_to_clipboard(str(est))
    except ValueError as e:
        print(f"\nInvalid input: {e}")
    except KeyboardInterrupt:
        print("\n[Aborted by user]")


def run_interactive() -> None:
    """
    Interactive mode when tbcalc is run with no CLI options.

    - Lets you pick a template:
        [1] Classic: Squat / Bench / Deadlift / Weighted Pull-Up
        [2] Front-Squat Block: Front Squat / Overhead Press / Deadlift / Weighted Pull-Up
        [3] Custom: choose lifts per slot

    - Asks for 1RMs/sets using the parse_one_rm_string logic
    - Handles WPU with bodyweight + set syntax
    - Builds args.lifts for build_program_markdown
    """
    print("Tactical Barbell Max Strength - Interactive Mode\n")

    # --- Title ---
    raw_title = input("Program title (leave blank for default): ").strip()
    if raw_title:
        title = raw_title
    else:
        title = f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"

    # --- Template selection ---
    print("\nSelect template:")
    print("  [1] Classic: Squat / Bench / Deadlift / Weighted Pull-Up")
    print(
        "  [2] Front-Squat Block: Front Squat / Overhead Press / Deadlift / Weighted Pull-Up"
    )
    print("  [3] Custom: choose lifts manually")
    template_choice = input("Template [1/2/3, default 1]: ").strip()
    if template_choice not in ("1", "2", "3"):
        template_choice = "1"

    lifts: dict[str, dict] = {}

    # ---------- Template 1 & 2: quick combos ----------
    if template_choice in ("1", "2"):
        if template_choice == "1":
            preset_exercises = ["squat", "bench press", "deadlift"]
        else:
            preset_exercises = ["front squat", "overhead press", "deadlift"]

        for ex_name in preset_exercises:
            one_rm, bar_weight = _prompt_for_exercise_1rm(ex_name)
            if one_rm is not None:
                lifts[ex_name] = {"one_rm": one_rm, "body_weight": None, "bar_weight": bar_weight}

    # ---------- Template 3: fully custom per slot ----------
    else:
        for slot in INTERACTIVE_LIFT_SLOTS:
            name = slot["name"]
            options = slot["options"]

            print(f"\n{name}:")
            for idx, opt in enumerate(options, start=1):
                print(f"  [{idx}] {format_exercise_name(opt['exercise_name'])}")
            print("  [s] Skip this slot")

            while True:
                choice = input("Select option: ").strip().lower()
                if choice in ("s", ""):
                    # skip this slot
                    break
                try:
                    idx = int(choice)
                except ValueError:
                    print("Invalid choice. Enter a number or 's' to skip.")
                    continue

                if not (1 <= idx <= len(options)):
                    print("Invalid option number. Try again.")
                    continue

                selected = options[idx - 1]
                ex_name = selected["exercise_name"]
                prompt_text = selected["prompt"]
                one_rm = prompt_lift_one_rm(prompt_text)
                if one_rm is None:
                    print("No valid 1RM entered; skipping this lift.")
                    break

                bar_weight = prompt_bar_weight(ex_name)
                lifts[ex_name] = {"one_rm": one_rm, "body_weight": None, "bar_weight": bar_weight}
                break  # only one selection per slot

    # ---------- Weighted pull-up (common for all templates) ----------
    weighted_pullup_entry: dict | None = None

    bw_raw = input(
        "\nBodyweight for weighted pull-ups (lb, blank to skip WPU): "
    ).strip()
    if bw_raw:
        try:
            bodyweight = int(bw_raw)
        except ValueError:
            print("Could not parse bodyweight; skipping weighted pull-ups.")
            bodyweight = None
        if bodyweight is not None:
            while True:
                wpu_raw = input(
                    "Weighted pull-up set (e.g. '35 4', '35x4', 'bw 4', 'bw x 4', blank to skip): "
                ).strip()
                if not wpu_raw:
                    break
                est = parse_weighted_pullup_string(bodyweight, wpu_raw)
                if est is None:
                    print(
                        "Could not parse that set. Try again (or press Enter to skip)."
                    )
                    continue
                weighted_pullup_entry = {
                    "one_rm": est,
                    "body_weight": bodyweight,
                }
                break

    if weighted_pullup_entry is not None:
        lifts["weighted pullup"] = weighted_pullup_entry

    # ---------- Extra exercises (custom template only) ----------
    if template_choice == "3":
        add_extra = input("\nWould you like to add extra exercises? (y/n, default n): ").strip().lower()

        if add_extra in ("y", "yes"):
            # Get list of all available exercises from EXERCISE_PROFILES
            from tbweightcalc.exercise_cluster import EXERCISE_PROFILES
            available = list(EXERCISE_PROFILES.keys())

            while True:
                print("\nAvailable exercises:")
                for idx, ex_name in enumerate(available, start=1):
                    print(f"  [{idx}] {format_exercise_name(ex_name)}")

                while True:
                    choice = input("Select exercise number: ").strip()
                    try:
                        idx = int(choice)
                    except ValueError:
                        print("Invalid choice. Enter a number.")
                        continue

                    if not (1 <= idx <= len(available)):
                        print("Invalid option number. Try again.")
                        continue

                    ex_name = available[idx - 1]

                    # Special handling for weighted pull-ups
                    if ex_name == "weighted pullup":
                        wpu_1rm, bodyweight = prompt_weighted_pullup_interactive()
                        if wpu_1rm is None:
                            print("No valid weighted pull-up data entered; skipping this exercise.")
                            break
                        lifts[ex_name] = {"one_rm": wpu_1rm, "body_weight": bodyweight, "bar_weight": 45.0}
                        print(f"Added {format_exercise_name(ex_name)} to your program.")
                        break

                    # Regular exercises (barbell lifts)
                    one_rm, bar_weight = _prompt_for_exercise_1rm(ex_name)
                    if one_rm is None:
                        print("No valid 1RM entered; skipping this exercise.")
                        break

                    lifts[ex_name] = {"one_rm": one_rm, "body_weight": None, "bar_weight": bar_weight}
                    print(f"Added {format_exercise_name(ex_name)} to your program.")
                    break

                # Ask if they want to add another
                add_another = input("\nAdd another exercise? (y/n, default n): ").strip().lower()
                if add_another not in ("y", "yes"):
                    break

    # ---------- Week selection ----------
    week_input = input("\nWeek (1–6 or 'all', default 'all'): ").strip().lower()
    if not week_input:
        week = "all"
    else:
        week = week_input

    # ---------- Output mode ----------
    out_mode = input("Output: [t]ext, [p]df, [b]oth (default b): ").strip().lower()
    if out_mode not in ("t", "p", "b"):
        out_mode = "b"

    # Build an argparse-like Namespace so we can reuse existing functions
    args = argparse.Namespace(
        week=week,
        lifts=lifts,
        onerm=None,
        title=title,
        pdf=None,
    )

    # ---------- Text output ----------
    screen_body = build_program_markdown(args, for_pdf=False)
    screen_output = f"# {title}\n\n{screen_body}"

    if out_mode in ("t", "b"):
        print(screen_output)
        copy_to_clipboard(screen_output)

    # ---------- PDF output ----------
    if out_mode in ("p", "b"):
        pdf_body = build_program_markdown(args, for_pdf=True)
        pdf_path = default_pdf_path(title)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_to_pdf(pdf_body, str(pdf_path), title=title)
        print(f"\n[PDF saved to: {pdf_path}]")


# -------------------------------------------------------------------
# Main CLI entry point
# -------------------------------------------------------------------


def main() -> None:
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

    parser.add_argument("-sq", "--squat", help="Enter 1RM for Squat (e.g. 455 or 455.5)", type=float)

    parser.add_argument("-fsq", "--front-squat", help="Enter 1RM for Front Squat (e.g. 355 or 355.5)", type=float, dest="front_squat")

    parser.add_argument("-zsq", "--zercher-squat", help="Enter 1RM for Zercher Squat (e.g. 315 or 315.5)", type=float, dest="zercher_squat")

    parser.add_argument("-bp", "--bench", help="Enter 1RM for Bench Press (e.g. 250 or 250.5)", type=float)

    parser.add_argument("-ohp", "--overhead-press", help="Enter 1RM for Overhead Press (e.g. 185 or 185.5)", type=float, dest="overhead_press")

    parser.add_argument("-dl", "--deadlift", help="Enter 1RM for Deadlift (e.g. 500 or 500.5)", type=float)

    parser.add_argument("-zdl", "--zercher-deadlift", help="Enter 1RM for Zercher Deadlift (e.g. 405 or 405.5)", type=float, dest="zercher_deadlift")

    parser.add_argument("-tbdl", "--trap-bar-deadlift", help="Enter 1RM for Trap Bar Deadlift (e.g. 550 or 550.5)", type=float, dest="trap_bar_deadlift")

    parser.add_argument(
        "-wpu",
        "--weighted-pullup",
        help='Enter 1RM for Weighted Pull Up followed by bodyweight: "-wpu 245 200"',
        type=int,
        nargs=2,
    )

    parser.add_argument(
        "-1rm",
        "--onerepmax",
        help="Estimate 1RM: with args 'weight reps' or interactively with no args",
        type=int,
        nargs="*",
        dest="onerm",
    )

    parser.add_argument(
        "--title",
        help="Optional title for the program/PDF; if omitted, a default is used",
    )

    parser.add_argument(
        "--pdf",
        help="Optional explicit path for the PDF output; defaults to ~/Downloads/<title>.pdf",
    )

    # No arguments at all -> full interactive program mode
    if len(sys.argv) == 1:
        try:
            run_interactive()
        except KeyboardInterrupt:
            # Clean, quiet exit on Ctrl-C
            print("\n[Aborted by user]")
        return

    args = parser.parse_args()

    # If 1RM calculator flag is used, handle it first and exit
    if args.onerm is not None:
        if len(args.onerm) == 0:
            # No args -> interactive 1RM calculator
            prompt_one_rm()
            return
        elif len(args.onerm) == 2:
            weight, reps = args.onerm
            est = calculate_one_rm(weight, reps)
            print(f"Estimated 1RM: {est} lb")
            copy_to_clipboard(str(est))
            return
        else:
            print(
                "Error: --onerepmax expects either no arguments or exactly two (weight reps)."
            )
            return

    # Decide title
    if args.title:
        title = args.title
    else:
        title = f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"

    screen_formatter = PlainFormatter()
    pdf_formatter = MarkdownFormatter()

    # 1) Build plain text for screen (with visible ---)
    screen_body = build_program_markdown(
        args, for_pdf=False, formatter=screen_formatter
    )
    screen_output = f"{screen_formatter.heading(title, level=1)}\n\n{screen_body}"

    # Print to stdout
    print(screen_output)

    # 2) Copy to clipboard (best-effort; works when run on macOS host)
    copy_to_clipboard(screen_output)

    # 3) Build markdown for PDF (with page breaks, no visible hr)
    pdf_body = build_program_markdown(args, for_pdf=True, formatter=pdf_formatter)

    # Determine PDF path:
    #   - If user passed --pdf, honor that
    #   - Otherwise, default to ~/Downloads/<title>.pdf
    if args.pdf:
        pdf_path = Path(os.path.expanduser(args.pdf))
    else:
        pdf_path = default_pdf_path(title)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate the PDF
    markdown_to_pdf(pdf_body, str(pdf_path), title=title)

    # Echo where the PDF went
    print(f"\n[PDF saved to: {pdf_path}]")


if __name__ == "__main__":
    main()
