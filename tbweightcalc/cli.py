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
from tbweightcalc.onerm import calculate_one_rm
from tbweightcalc.program import apply_markdown, markdown_to_pdf


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


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


def build_program_markdown(args: argparse.Namespace, for_pdf: bool = False) -> str:
    """
    Build the Tactical Barbell program markdown.

    for_pdf=False:
        - includes visible '---' horizontal rules between weeks

    for_pdf=True:
        - uses raw '\\pagebreak' between weeks (no visible HR in PDF)
    """
    lines: list[str] = []

    week_percentages = {
        1: "70%",
        2: "80%",
        3: "90%",
        4: "75%",
        5: "85%",
        6: "95%",
    }

    # If week is specified as single week, use that; if "all" or None, do 1–6.
    if args.week and args.week != "all":
        weeks = [int(args.week)]
    else:
        weeks = list(range(1, 7))

    for week in weeks:
        # Week header
        lines.append(apply_markdown(f"WEEK {week} - {week_percentages[week]}", "h2"))
        lines.append("")

        # Squat
        if args.squat is not None:
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
        if args.bench is not None:
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
        if args.deadlift is not None:
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
        if args.weighted_pullup is not None:
            one_rm, bodyweight = args.weighted_pullup
            lines.append(
                tb.Program.print_exercise(
                    exercise="weighted pullup",
                    oneRepMax=one_rm,
                    body_weight=bodyweight,
                    week=week,
                    print_1rm=True,
                )
            )

        # Separator between weeks (only if multiple weeks)
        if week != weeks[-1]:
            if for_pdf:
                # Raw page break for PDF
                lines.append(r"\pagebreak")
            else:
                # Visible HR for terminal markdown
                lines.append("")
                lines.append(apply_markdown("", "hr"))
                lines.append("")

    return "\n".join(lines).rstrip()


# -------------------------------------------------------------------
# 1RM parsing helpers
# -------------------------------------------------------------------


def parse_one_rm_string(raw: str) -> int | None:
    """
    Parse generic 1RM input string.

    Accepts:
      - '' or whitespace -> None
      - '455'            -> 455 (assumed true 1RM)
      - '240 5'          -> estimate 1RM from 240 x 5
      - '240x5', '240X5' -> same as above
    """
    raw = raw.strip()
    if not raw:
        return None

    # '240x5' or '240X5'
    m = re.match(r"^(\d+)[xX](\d+)$", raw)
    if m:
        weight = float(m.group(1))
        reps = int(m.group(2))
        return calculate_one_rm(weight, reps)

    parts = raw.split()

    # '240 5'
    if len(parts) == 2 and all(p.isdigit() for p in parts):
        weight = float(parts[0])
        reps = int(parts[1])
        return calculate_one_rm(weight, reps)

    # Single integer '455' -> literal 1RM
    if len(parts) == 1 and parts[0].isdigit():
        return int(parts[0])

    return None


def parse_weighted_pullup_string(bodyweight: int, raw: str) -> int | None:
    """
    Parse weighted pull-up input given a bodyweight.

    bodyweight: integer body weight in lb.

    raw: one of:
      - '' or whitespace                -> returns None
      - '35 4'                          -> +35 lb for 4 reps
      - '35x4' or '35X4'                -> +35 lb for 4 reps
      - '0 4'                           -> bodyweight-only for 4 reps
      - 'bw'                            -> bodyweight-only for 1 rep
      - 'bwx4', 'bw x 4', 'bw 4'        -> bodyweight-only for 4 reps
      - '45'                            -> +45 lb for 1 rep

    Returns:
      - total 1RM (bodyweight + added) as an int
      - None if input is blank or invalid
    """
    raw = raw.strip()
    if not raw:
        return None

    lower = raw.lower()

    added: int
    reps: int

    # --- BW-only shorthands ---
    if lower == "bw":
        added = 0
        reps = 1
    else:
        # "bwx4", "bw x 4", "bw 4"
        m_bw = re.match(r"^bw\s*[xX]?\s*(\d+)$", lower)
        if m_bw:
            added = 0
            reps = int(m_bw.group(1))
        else:
            # --- Numeric styles ---

            # '35x4' or '35X4'
            m = re.match(r"^(\d+)[xX](\d+)$", raw)
            if m:
                added = int(m.group(1))
                reps = int(m.group(2))
            else:
                parts = raw.split()

                # '35 4' style
                if len(parts) == 2 and all(p.isdigit() for p in parts):
                    added = int(parts[0])
                    reps = int(parts[1])

                # Single number '45' -> +45 lb for 1 rep
                elif len(parts) == 1 and parts[0].isdigit():
                    added = int(parts[0])
                    reps = 1
                else:
                    return None

    total_weight = bodyweight + added
    return calculate_one_rm(total_weight, reps)


# -------------------------------------------------------------------
# Interactive helpers
# -------------------------------------------------------------------


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
    Asks for title, 1RMs (or sets to estimate 1RMs), week selection,
    and output mode (text/pdf/both).
    """
    print("Tactical Barbell Max Strength - Interactive Mode\n")

    # --- Title ---
    raw_title = input("Program title (leave blank for default): ").strip()
    if raw_title:
        title = raw_title
    else:
        title = f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"

    # --- Squat / Bench / Deadlift 1RMs (with retry on invalid) ---
    squat = prompt_lift_one_rm("Squat")
    bench = prompt_lift_one_rm("Bench press")
    deadlift = prompt_lift_one_rm("Deadlift")

    # --- Weighted pull-ups (with retry for BW and set) ---
    wpu_one_rm, wpu_bodyweight = prompt_weighted_pullup_interactive()
    if wpu_one_rm is not None and wpu_bodyweight is not None:
        weighted_pullup: tuple[int, int] | None = (wpu_one_rm, wpu_bodyweight)
    else:
        weighted_pullup = None

    # --- Week selection ---
    week_input = input("Week (1–6 or 'all', default 'all'): ").strip().lower()
    if not week_input:
        week = "all"
    else:
        week = week_input

    # --- Output mode ---
    out_mode = input("Output: [t]ext, [p]df, [b]oth (default b): ").strip().lower()
    if out_mode not in ("t", "p", "b"):
        out_mode = "b"

    # Build an argparse-like Namespace so we can reuse existing functions
    args = argparse.Namespace(
        week=week,
        squat=squat,
        bench=bench,
        deadlift=deadlift,
        weighted_pullup=weighted_pullup,
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

    # 1) Build markdown for screen (with visible ---)
    screen_body = build_program_markdown(args, for_pdf=False)
    screen_output = f"# {title}\n\n{screen_body}"

    # Print to stdout
    print(screen_output)

    # 2) Copy to clipboard (best-effort; works when run on macOS host)
    copy_to_clipboard(screen_output)

    # 3) Build markdown for PDF (with page breaks, no visible hr)
    pdf_body = build_program_markdown(args, for_pdf=True)

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
