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
from tbweightcalc.config import Config, load_config
from tbweightcalc.formatting import Formatter, MarkdownFormatter, PlainFormatter
from tbweightcalc.onerm import calculate_one_rm
from tbweightcalc.program import markdown_to_pdf
from tbweightcalc.sessions import SessionStore


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


def _prompt_for_exercise_1rm(exercise_name: str, store=None) -> tuple[int | None, float, str | None]:
    """
    Look up the interactive prompt text for the given exercise_name
    from INTERACTIVE_LIFT_SLOTS and run prompt_lift_one_rm on it.

    Returns (1RM, bar_weight, bar_label) where 1RM can be None if skipped.
    """
    for slot in INTERACTIVE_LIFT_SLOTS:
        for opt in slot["options"]:
            if opt["exercise_name"] == exercise_name:
                one_rm = prompt_lift_one_rm(opt["prompt"])
                if one_rm is None:
                    return (None, 45.0, None)
                bar_weight, bar_label = prompt_bar_weight(exercise_name, store=store)
                return (one_rm, bar_weight, bar_label)
    # If not found in config, just fall back to a generic prompt.
    generic = f"{format_exercise_name(exercise_name)} 1RM or set (e.g. '225', '200 5', '200x5', blank to skip): "
    one_rm = prompt_lift_one_rm(generic)
    if one_rm is None:
        return (None, 45.0, None)
    bar_weight, bar_label = prompt_bar_weight(exercise_name, store=store)
    return (one_rm, bar_weight, bar_label)


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
    config: Config | None = None,
) -> str:
    """
    Build the Tactical Barbell program markdown.

    - If args.lifts is present, it can be either:
        - A dict: { "squat": {"one_rm": 455, "body_weight": None}, ... }
        - A list: [{"exercise": "squat", "one_rm": 455, "body_weight": None}, ...]
      and we render based on that.
    - Otherwise, we fall back to the legacy fixed fields:
        args.squat, args.bench, args.deadlift, args.weighted_pullup, etc.
    """
    # Load config if not provided
    if config is None:
        config = load_config()

    fmt = formatter
    if fmt is None:
        if for_pdf:
            fmt = MarkdownFormatter(formatting_config=config.formatting)
        else:
            fmt = PlainFormatter(formatting_config=config.formatting)

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

    # ----- Build a unified lifts structure -----
    if hasattr(args, "lifts") and args.lifts:
        # Check if lifts is a list (new format) or dict (legacy format)
        if isinstance(args.lifts, list):
            lifts_list = args.lifts
        else:
            # Convert dict to list for backwards compatibility
            lifts_list = []
            for ex_name, cfg in args.lifts.items():
                lifts_list.append({
                    "exercise": ex_name,
                    "one_rm": cfg["one_rm"],
                    "body_weight": cfg.get("body_weight"),
                    "bar_weight": cfg.get("bar_weight", 45.0),
                })
    else:
        # Legacy path — build from old fields for CLI flags.
        lifts_list = []
        if getattr(args, "squat", None) is not None:
            lifts_list.append({"exercise": "squat", "one_rm": round(args.squat), "body_weight": None, "bar_weight": 45.0})
        if getattr(args, "front_squat", None) is not None:
            lifts_list.append({"exercise": "front squat", "one_rm": round(args.front_squat), "body_weight": None, "bar_weight": 45.0})
        if getattr(args, "zercher_squat", None) is not None:
            lifts_list.append({"exercise": "zercher squat", "one_rm": round(args.zercher_squat), "body_weight": None, "bar_weight": 45.0})
        if getattr(args, "bench", None) is not None:
            lifts_list.append({"exercise": "bench press", "one_rm": round(args.bench), "body_weight": None, "bar_weight": 45.0})
        if getattr(args, "overhead_press", None) is not None:
            lifts_list.append({
                "exercise": "overhead press",
                "one_rm": round(args.overhead_press),
                "body_weight": None,
                "bar_weight": 45.0,
            })
        if getattr(args, "deadlift", None) is not None:
            lifts_list.append({"exercise": "deadlift", "one_rm": round(args.deadlift), "body_weight": None, "bar_weight": 45.0})
        if getattr(args, "zercher_deadlift", None) is not None:
            lifts_list.append({"exercise": "zercher deadlift", "one_rm": round(args.zercher_deadlift), "body_weight": None, "bar_weight": 45.0})
        if getattr(args, "trap_bar_deadlift", None) is not None:
            lifts_list.append({"exercise": "trap bar deadlift", "one_rm": round(args.trap_bar_deadlift), "body_weight": None, "bar_weight": 45.0})
        wpu = getattr(args, "weighted_pullup", None)
        if wpu is not None:
            one_rm, bw = wpu
            lifts_list.append({"exercise": "weighted pullup", "one_rm": one_rm, "body_weight": bw, "bar_weight": 45.0})

    for week in weeks:
        lines.append(fmt.heading(f"WEEK {week} - {week_percentages[week]}", level=2))
        lines.append("")

        for lift_cfg in lifts_list:
            ex_name = lift_cfg["exercise"]
            one_rm = lift_cfg["one_rm"]
            body_weight = lift_cfg.get("body_weight")
            bar_weight = lift_cfg.get("bar_weight", 45.0)
            bar_label = lift_cfg.get("bar_label")

            lines.append(
                tb.Program.print_exercise(
                    exercise=ex_name,
                    oneRepMax=one_rm,
                    body_weight=body_weight,
                    bar_weight=bar_weight,
                    bar_label=bar_label,
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


def evaluate_weight_expression(base_weight: float, expression: str) -> float:
    """
    Evaluate a simple math expression applied to a base weight.

    Supports:
      '+ 10%'       -> base_weight + (base_weight * 0.10)
      '- 5%'        -> base_weight - (base_weight * 0.05)
      '+ 20'        -> base_weight + 20
      '+ 20 lbs'    -> base_weight + 20
      '- 10 lb'     -> base_weight - 10

    Returns the calculated weight as a float.
    Raises ValueError if the expression cannot be parsed.
    """
    expr = expression.strip()
    match = re.match(r'^([+\-])\s*(\d+(?:\.\d+)?)\s*(%|lbs?)?$', expr, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid expression: {expression}")

    operator = match.group(1)
    value = float(match.group(2))
    unit = match.group(3)

    if unit and unit.strip().lower().startswith('%'):
        adjustment = base_weight * (value / 100.0)
    else:
        adjustment = value

    if operator == '+':
        return base_weight + adjustment
    else:
        return base_weight - adjustment


def parse_one_rm_string(raw: str) -> int | None:
    """
    Parse generic 1RM input string.

    Accepts:
      - '' or whitespace              -> None
      - '455' or '255.6'              -> 455 or 256 (rounded to nearest int)
      - '240 5' or '240.5 5'          -> estimate 1RM from weight x reps (rounded)
      - '240x5', '240 x5',
        '240x 5', '240 x 5'           -> same as above
      - '240 + 10%'                   -> 240 + 10% of 240 = 264
      - '240 - 5%'                    -> 240 - 5% of 240 = 228
      - '240 + 20' or '240 + 20 lbs'  -> 240 + 20 = 260
      - '240 - 10' or '240 - 10 lb'   -> 240 - 10 = 230
    """
    raw = raw.strip()
    if not raw:
        return None

    # Math expressions: '240 + 10%', '240-5%', '240 + 20', '240 - 10 lbs', etc.
    expr_match = re.match(
        r'^(\d+(?:\.\d+)?)\s*([+\-]\s*\d+(?:\.\d+)?\s*(?:%|lbs?)?)$',
        raw,
        re.IGNORECASE,
    )
    if expr_match:
        base = float(expr_match.group(1))
        expression = expr_match.group(2)
        try:
            result = evaluate_weight_expression(base, expression)
            return round(result)
        except ValueError:
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


def _lift_summary_line(lift: dict) -> str:
    """
    Return a concise one-line summary for a single lift entry, e.g.:
      'Squat: 455#'
      'Deadlift (Trap Bar - 60#): 380#'
      'Weighted Pull-Up: 85# added @ BW 212#'
    """
    name = format_exercise_name(lift["exercise"])
    one_rm = lift["one_rm"]
    bw = lift.get("body_weight")
    bar_lbl = lift.get("bar_label")
    bar_wt = lift.get("bar_weight", 45.0)

    if bw is not None:
        added = one_rm - bw
        return f"{name}: {added}# added @ BW {bw}#"

    bar_suffix = ""
    if bar_lbl and bar_wt != 45.0:
        w = int(bar_wt) if bar_wt == int(bar_wt) else bar_wt
        bar_suffix = f" ({bar_lbl} - {w}#)"
    elif bar_lbl:
        bar_suffix = f" ({bar_lbl})"
    elif bar_wt != 45.0:
        w = int(bar_wt) if bar_wt == int(bar_wt) else bar_wt
        bar_suffix = f" ({w}# bar)"

    return f"{name}{bar_suffix}: {one_rm}#"


def _review_and_edit_lifts(lifts: list[dict], store=None) -> list[dict]:
    """
    Show a numbered summary of all entered lifts and let the user
    re-enter any entry before continuing.

    Typing a lift number re-prompts that lift.
    Typing 'c' (or pressing Enter) accepts the list and returns it.
    """
    if not lifts:
        return lifts

    while True:
        print("\n--- Review Your Lifts ---")
        for i, lift in enumerate(lifts, start=1):
            print(f"  [{i}] {_lift_summary_line(lift)}")
        print("  [c] Continue / done")

        choice = input("Edit # or [c] to continue: ").strip().lower()

        if choice in ("c", ""):
            break

        try:
            idx = int(choice)
        except ValueError:
            print("Enter a lift number to edit, or 'c' to continue.")
            continue

        if not (1 <= idx <= len(lifts)):
            print(f"Please enter a number between 1 and {len(lifts)}.")
            continue

        lift = lifts[idx - 1]
        ex_name = lift["exercise"]

        if ex_name == "weighted pullup":
            bw = lift.get("body_weight")
            total_1rm = lift["one_rm"]
            added = total_1rm - bw if bw else total_1rm
            print(f"\nRe-entering Weighted Pull-Up (current: {added}# added @ BW {bw}#)")

            bw_raw = input(f"Bodyweight in lbs (current {bw}#, blank to keep): ").strip()
            new_bw = bw
            if bw_raw:
                try:
                    new_bw = int(bw_raw)
                except ValueError:
                    print("Invalid bodyweight; keeping current.")

            wpu_raw = input(
                "WPU set (e.g. '35 4', '35x4', blank to keep current): "
            ).strip()
            if wpu_raw:
                est = parse_weighted_pullup_string(new_bw, wpu_raw)
                if est is not None:
                    lifts[idx - 1]["one_rm"] = est
                    lifts[idx - 1]["body_weight"] = new_bw
                    print(f"Updated: {_lift_summary_line(lifts[idx - 1])}")
                else:
                    print("Could not parse WPU input; keeping current values.")
            elif new_bw != bw:
                # BW changed, no new set entered — preserve the added weight
                lifts[idx - 1]["one_rm"] = new_bw + added
                lifts[idx - 1]["body_weight"] = new_bw
                print(f"Updated: {_lift_summary_line(lifts[idx - 1])}")
        else:
            print(f"\nRe-entering {format_exercise_name(ex_name)} (current: {lift['one_rm']}#)")
            one_rm, bar_weight, bar_label = _prompt_for_exercise_1rm(ex_name, store=store)
            if one_rm is not None:
                lifts[idx - 1]["one_rm"] = one_rm
                lifts[idx - 1]["bar_weight"] = bar_weight
                lifts[idx - 1]["bar_label"] = bar_label
                print(f"Updated: {_lift_summary_line(lifts[idx - 1])}")
            else:
                print("No valid 1RM entered; keeping current value.")

    return lifts


def prompt_bar_weight(exercise_name: str, store=None) -> tuple[float, str | None]:
    """
    Prompt for bar weight with default of 45 pounds and optional label.
    If a SessionStore is provided, saved custom bars are shown for quick recall.
    After entering a non-default weight with a label, offers to save it.

    Returns:
      - tuple of (bar_weight, bar_label) where bar_label can be None
    """
    bars = store.list_bars() if store is not None else []

    while True:
        if bars:
            print(f"  Saved bars:")
            for i, b in enumerate(bars, start=1):
                w = int(b["weight"]) if b["weight"] == int(b["weight"]) else b["weight"]
                print(f"    [{i}] {b['name']} ({w}#)")

        hint = f"1-{len(bars)} for saved bar, or " if bars else ""
        raw = input(f"Bar weight for {exercise_name} ({hint}default 45): ").strip()

        if not raw:
            return (45.0, None)

        # Check if it's a saved bar index
        if bars:
            try:
                idx = int(raw)
                if 1 <= idx <= len(bars):
                    b = bars[idx - 1]
                    return (b["weight"], b["name"])
            except ValueError:
                pass

        # Parse as a weight
        try:
            bar_weight = float(raw)
            if bar_weight <= 0:
                print("Bar weight must be greater than 0. Try again or press Enter for default (45).")
                continue
        except ValueError:
            print("Invalid input. Enter a number or press Enter for default (45).")
            continue

        label = input("Optional label for bar (e.g. 'C-70', blank to skip): ").strip()

        # Offer to save as a custom bar if it has a label and a non-standard weight
        if store is not None and label and bar_weight != 45.0:
            save_raw = input(f"Save '{label}' ({int(bar_weight) if bar_weight == int(bar_weight) else bar_weight}#) as a custom bar for future use? (y/n): ").strip().lower()
            if save_raw in ("y", "yes"):
                store.save_bar(label, bar_weight)
                print(f"[Saved bar '{label}']")

        return (bar_weight, label if label else None)


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


def _prompt_save_session(lifts: list[dict], store: SessionStore, default_name: str | None = None) -> None:
    """After generating a program, offer to save the lifts as a named session.

    If default_name is provided (e.g. the program title), it is pre-filled so
    the user can just press Enter to accept it.
    """
    if default_name:
        prompt = f"\nSave this session? Press Enter for '{default_name}', type a new name, or 'n' to skip: "
    else:
        prompt = "\nSave this session? Enter a name (or press Enter to skip): "

    raw = input(prompt).strip()
    if raw.lower() == "n":
        return
    name = raw or default_name
    if not name:
        return
    session = store.save_session(name, lifts)
    action = "Updated" if "updated" in session else "Saved"
    print(f"[{action} session '{session['name']}' ({session['id']})]")


def _print_sessions(sessions: list[dict]) -> None:
    if not sessions:
        print("  (no saved sessions)")
        return
    for i, s in enumerate(sessions, start=1):
        date = s.get("updated") or s["created"]
        print(f"  [{i}] {s['name']}  ({date})  id:{s['id']}")


def run_interactive() -> None:
    """
    Interactive mode when tbcalc is run with no CLI options.

    - Lets you pick a template:
        [1] Classic: Squat / Bench / Deadlift / Weighted Pull-Up
        [2] Front-Squat Block: Front Squat / Overhead Press / Deadlift / Weighted Pull-Up
        [3] Zercher Block: Zercher Squat / Bench Press / Deadlift / Weighted Pull-Up
        [4] Custom: choose lifts per slot

    - Asks for 1RMs/sets using the parse_one_rm_string logic
    - Handles WPU with bodyweight + set syntax
    - Builds args.lifts for build_program_markdown
    """
    print("Tactical Barbell Max Strength - Interactive Mode\n")

    store = SessionStore()

    # --- Offer to load a saved session ---
    sessions = store.list_sessions()
    lifts: list[dict] = []
    loaded_from_session = False

    loaded_session_name: str | None = None

    if sessions:
        print("Saved sessions:")
        _print_sessions(sessions)
        load_raw = input("\nLoad a session? Enter number/name or press Enter to start fresh: ").strip()
        if load_raw:
            session = store.load_session(load_raw)
            if session:
                lifts = [dict(lift) for lift in session["lifts"]]
                loaded_from_session = True
                loaded_session_name = session["name"]
                print(f"[Loaded '{session['name']}']")
            else:
                print(f"No session found for '{load_raw}'; starting fresh.")

    # --- Title ---
    # When editing a saved session, pre-fill its name as the title default.
    if loaded_session_name:
        title_prompt = f"\nProgram title (Enter for '{loaded_session_name}'): "
    else:
        title_prompt = "\nProgram title (leave blank for default): "
    raw_title = input(title_prompt).strip()
    if raw_title:
        title = raw_title
    elif loaded_session_name:
        title = loaded_session_name
    else:
        title = f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"

    if loaded_from_session:
        # Skip template/lift entry; go straight to review/edit
        lifts = _review_and_edit_lifts(lifts, store=store)
    else:
        lifts = []

        # --- Template selection ---
        print("\nSelect template:")
        print("  [1] Classic: Squat / Bench / Deadlift / Weighted Pull-Up")
        print(
            "  [2] Front-Squat Block: Front Squat / Overhead Press / Deadlift / Weighted Pull-Up"
        )
        print(
            "  [3] Zercher Block: Zercher Squat / Bench Press / Deadlift / Weighted Pull-Up"
        )
        print("  [4] Custom: choose lifts manually")
        template_choice = input("Template [1/2/3/4, default 1]: ").strip()
        if template_choice not in ("1", "2", "3", "4"):
            template_choice = "1"

        # ---------- Template 1, 2 & 3: quick combos ----------
        if template_choice in ("1", "2", "3"):
            if template_choice == "1":
                preset_exercises = ["squat", "bench press", "deadlift"]
            elif template_choice == "2":
                preset_exercises = ["front squat", "overhead press", "deadlift"]
            else:  # template_choice == "3"
                preset_exercises = ["zercher squat", "bench press", "deadlift"]

            for ex_name in preset_exercises:
                one_rm, bar_weight, bar_label = _prompt_for_exercise_1rm(ex_name, store=store)
                if one_rm is not None:
                    lifts.append({"exercise": ex_name, "one_rm": one_rm, "body_weight": None, "bar_weight": bar_weight, "bar_label": bar_label})

        # ---------- Template 4: fully custom per slot ----------
        else:
            for slot in INTERACTIVE_LIFT_SLOTS:
                slot_name = slot["name"]
                options = slot["options"]

                print(f"\n{slot_name}:")
                for idx, opt in enumerate(options, start=1):
                    print(f"  [{idx}] {format_exercise_name(opt['exercise_name'])}")
                print("  [s] Skip this slot")

                while True:
                    choice = input("Select option: ").strip().lower()
                    if choice in ("s", ""):
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

                    bar_weight, bar_label = prompt_bar_weight(ex_name, store=store)
                    lifts.append({"exercise": ex_name, "one_rm": one_rm, "body_weight": None, "bar_weight": bar_weight, "bar_label": bar_label})
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
            lifts.append({
                "exercise": "weighted pullup",
                "one_rm": weighted_pullup_entry["one_rm"],
                "body_weight": weighted_pullup_entry["body_weight"],
                "bar_weight": 45.0,
            })

        # ---------- Extra exercises (custom template only) ----------
        if template_choice == "4":
            add_extra = input("\nWould you like to add extra exercises? (y/n, default n): ").strip().lower()

            if add_extra in ("y", "yes"):
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

                        if ex_name == "weighted pullup":
                            wpu_1rm, bodyweight = prompt_weighted_pullup_interactive()
                            if wpu_1rm is None:
                                print("No valid weighted pull-up data entered; skipping this exercise.")
                                break
                            lifts.append({"exercise": ex_name, "one_rm": wpu_1rm, "body_weight": bodyweight, "bar_weight": 45.0})
                            print(f"Added {format_exercise_name(ex_name)} to your program.")
                            break

                        one_rm, bar_weight, bar_label = _prompt_for_exercise_1rm(ex_name, store=store)
                        if one_rm is None:
                            print("No valid 1RM entered; skipping this exercise.")
                            break

                        lifts.append({"exercise": ex_name, "one_rm": one_rm, "body_weight": None, "bar_weight": bar_weight, "bar_label": bar_label})
                        print(f"Added {format_exercise_name(ex_name)} to your program.")
                        break

                    add_another = input("\nAdd another exercise? (y/n, default n): ").strip().lower()
                    if add_another not in ("y", "yes"):
                        break

        # ---------- Review & edit all lifts before generating output ----------
        lifts = _review_and_edit_lifts(lifts, store=store)

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

    # ---------- Save session ----------
    _prompt_save_session(lifts, store, default_name=title)


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

    parser.add_argument(
        "--config",
        help="Path to custom config YAML file (defaults to ~/.config/tbcalc/config.yaml)",
        type=Path,
    )

    session_group = parser.add_argument_group("session management")
    session_group.add_argument(
        "--list-sessions",
        action="store_true",
        help="List all saved sessions and exit",
    )
    session_group.add_argument(
        "--load-session",
        metavar="NAME",
        help="Load a saved session by name, number, or id and generate the program",
    )
    session_group.add_argument(
        "--delete-session",
        metavar="NAME",
        help="Delete a saved session by name, number, or id and exit",
    )
    session_group.add_argument(
        "--save-session",
        metavar="NAME",
        help="Save the current lifts as a named session after generating",
    )

    bar_group = parser.add_argument_group("custom bar management")
    bar_group.add_argument(
        "--list-bars",
        action="store_true",
        help="List all saved custom bars and exit",
    )
    bar_group.add_argument(
        "--save-bar",
        nargs=2,
        metavar=("NAME", "WEIGHT"),
        help='Save a custom bar by name and weight, e.g. --save-bar "Trap Bar" 60',
    )
    bar_group.add_argument(
        "--delete-bar",
        metavar="NAME",
        help="Delete a saved custom bar by name and exit",
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

    # Load config
    config = load_config(args.config if hasattr(args, 'config') and args.config else None)

    store = SessionStore()

    # --- Bar management commands (exit after) ---
    if args.list_bars:
        bars = store.list_bars()
        if not bars:
            print("No saved custom bars.")
        else:
            print("Saved custom bars:")
            for b in bars:
                w = int(b["weight"]) if b["weight"] == int(b["weight"]) else b["weight"]
                print(f"  {b['name']} ({w}#)")
        return

    if args.save_bar:
        name, weight_str = args.save_bar
        try:
            weight = float(weight_str)
        except ValueError:
            print(f"Invalid weight '{weight_str}'. Must be a number.")
            return
        store.save_bar(name, weight)
        w = int(weight) if weight == int(weight) else weight
        print(f"[Saved bar '{name}' ({w}#)]")
        return

    if args.delete_bar:
        if store.delete_bar(args.delete_bar):
            print(f"Deleted bar '{args.delete_bar}'.")
        else:
            print(f"No bar found named '{args.delete_bar}'.")
        return

    # --- Session management commands (exit after) ---
    if args.list_sessions:
        sessions = store.list_sessions()
        if not sessions:
            print("No saved sessions.")
        else:
            print("Saved sessions:")
            _print_sessions(sessions)
        return

    if args.delete_session:
        if store.delete_session(args.delete_session):
            print(f"Deleted session '{args.delete_session}'.")
        else:
            print(f"No session found for '{args.delete_session}'.")
        return

    # --- Load session lifts ---
    if args.load_session:
        session = store.load_session(args.load_session)
        if session is None:
            print(f"No session found for '{args.load_session}'.")
            return
        args.lifts = session["lifts"]
        print(f"[Loaded session '{session['name']}']")

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

    screen_formatter = PlainFormatter(formatting_config=config.formatting)
    pdf_formatter = MarkdownFormatter(formatting_config=config.formatting)

    # 1) Build plain text for screen (with visible ---)
    screen_body = build_program_markdown(
        args, for_pdf=False, formatter=screen_formatter, config=config
    )
    screen_output = f"{screen_formatter.heading(title, level=1)}\n\n{screen_body}"

    # Print to stdout
    print(screen_output)

    # 2) Copy to clipboard (best-effort; works when run on macOS host)
    if config.output.copy_to_clipboard:
        copy_to_clipboard(screen_output)

    # 3) Build markdown for PDF (with page breaks, no visible hr)
    pdf_body = build_program_markdown(args, for_pdf=True, formatter=pdf_formatter, config=config)

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

    # 4) Save session if requested
    if args.save_session:
        lifts_list = args.lifts if hasattr(args, "lifts") and args.lifts else []
        if lifts_list:
            session = store.save_session(args.save_session, lifts_list)
            action = "Updated" if "updated" in session else "Saved"
            print(f"[{action} session '{session['name']}' ({session['id']})]")


if __name__ == "__main__":
    main()
