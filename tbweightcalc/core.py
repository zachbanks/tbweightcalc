"""
Core business logic for tbweightcalc.

All computation, parsing, and formatting lives here with no dependency on
CLI argument parsing, user I/O, or any specific interface layer.

Import from this module in CLI, TUI, API, or any other consumer:

    from tbweightcalc.core import build_program_markdown, parse_one_rm_string
"""
from __future__ import annotations

import datetime
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import tbweightcalc as tb
from tbweightcalc.config import Config, load_config
from tbweightcalc.formatting import Formatter, MarkdownFormatter, PlainFormatter
from tbweightcalc.onerm import calculate_one_rm
from tbweightcalc.program import markdown_to_pdf  # re-exported for convenience

__all__ = [
    "INTERACTIVE_LIFT_SLOTS",
    "_ADJUSTMENT_PRESETS",
    "_apply_lift_adjustment",
    "_lift_summary_line",
    "build_program_markdown",
    "copy_to_clipboard",
    "default_pdf_path",
    "evaluate_weight_expression",
    "format_exercise_name",
    "markdown_to_pdf",
    "parse_one_rm_string",
    "parse_weighted_pullup_string",
]


# ---------------------------------------------------------------------------
# Exercise / slot data
# ---------------------------------------------------------------------------

def format_exercise_name(exercise_name: str) -> str:
    """Format exercise name for display: 'rdl' → 'RDL', others → Title Case."""
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


# ---------------------------------------------------------------------------
# 1RM parsing
# ---------------------------------------------------------------------------

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

    return base_weight + adjustment if operator == '+' else base_weight - adjustment


def parse_one_rm_string(raw: str) -> int | None:
    """
    Parse generic 1RM input string.

    Accepts:
      - '' or whitespace              -> None
      - '455' or '255.6'              -> 455 or 256 (rounded)
      - '240 5' or '240x5'           -> estimate 1RM from set
      - '240 + 10%' / '240 - 5%'    -> percentage adjustment
      - '240 + 20' / '240 - 10 lbs' -> absolute adjustment
    """
    raw = raw.strip()
    if not raw:
        return None

    # Math expressions: '240 + 10%', '240-5%', '240 + 20', etc.
    expr_match = re.match(
        r'^(\d+(?:\.\d+)?)\s*([+\-]\s*\d+(?:\.\d+)?\s*(?:%|lbs?)?)$',
        raw,
        re.IGNORECASE,
    )
    if expr_match:
        base = float(expr_match.group(1))
        try:
            return round(evaluate_weight_expression(base, expr_match.group(2)))
        except ValueError:
            return None

    # '240x5' / '240 x5' etc.
    m = re.match(r"^(\d+(?:\.\d+)?)\s*[xX]\s*(\d+)$", raw)
    if m:
        return calculate_one_rm(float(m.group(1)), int(m.group(2)))

    parts = raw.split()

    if len(parts) == 2:
        try:
            return calculate_one_rm(float(parts[0]), int(parts[1]))
        except ValueError:
            return None

    if len(parts) == 1:
        try:
            return round(float(parts[0]))
        except ValueError:
            return None

    return None


def parse_weighted_pullup_string(bodyweight: int, raw: str) -> int | None:
    """
    Parse weighted pull-up input given a bodyweight.

    Accepts added-weight + reps formats ('35 4', '35x4', 'bw 4', 'bw', '45').
    Returns total 1RM (bodyweight + added) as int, or None if blank/invalid.
    """
    raw = raw.strip()
    if not raw:
        return None

    lower = raw.lower()
    added: float
    reps: int

    if lower == "bw":
        added, reps = 0, 1
    else:
        m_bw = re.match(r"^bw\s*[xX]?\s*(\d+)$", lower)
        if m_bw:
            added, reps = 0, int(m_bw.group(1))
        else:
            m = re.match(r"^(\d+(?:\.\d+)?)\s*[xX]\s*(\d+)$", raw)
            if m:
                added, reps = float(m.group(1)), int(m.group(2))
            else:
                parts = raw.split()
                if len(parts) == 2:
                    try:
                        added, reps = float(parts[0]), int(parts[1])
                    except ValueError:
                        return None
                elif len(parts) == 1:
                    try:
                        added, reps = float(parts[0]), 1
                    except ValueError:
                        return None
                else:
                    return None

    return calculate_one_rm(bodyweight + added, reps)


# ---------------------------------------------------------------------------
# Adjustment presets
# ---------------------------------------------------------------------------

_ADJUSTMENT_PRESETS = [
    ("+2.5%",  2.5),
    ("+5%",    5.0),
    ("+10%",  10.0),
    ("-2.5%", -2.5),
    ("-5%",   -5.0),
    ("-10%", -10.0),
]


def _apply_lift_adjustment(lifts: list[dict], pct: float, exercise: str | None = None) -> list[dict]:
    """
    Return a new lifts list with one_rm values scaled by pct%.

    For WPU lifts (body_weight is set), the % applies to the added-weight
    portion only (one_rm - body_weight). body_weight is never modified.
    """
    result = []
    for lift in lifts:
        l = dict(lift)
        if exercise is None or l["exercise"].lower() == exercise.lower():
            if l.get("one_rm") is not None:
                bw = l.get("body_weight")
                if bw is not None:
                    added = l["one_rm"] - bw
                    l["one_rm"] = bw + round(added * (1 + pct / 100))
                else:
                    l["one_rm"] = round(l["one_rm"] * (1 + pct / 100))
        result.append(l)
    return result


# ---------------------------------------------------------------------------
# Program generation
# ---------------------------------------------------------------------------

def build_program_markdown(
    lifts: list[dict],
    week: str = "all",
    for_pdf: bool = False,
    formatter: Formatter | None = None,
    config: Config | None = None,
) -> str:
    """
    Build the Tactical Barbell program as Markdown text.

    Args:
        lifts:     List of lift dicts: {exercise, one_rm, body_weight, bar_weight, bar_label}
        week:      '1'–'6' for a single week, or 'all' for the full 6-week block
        for_pdf:   Use PDF-optimised formatting (page breaks, no visible HR)
        formatter: Override the default Formatter
        config:    Override loaded config
    """
    if config is None:
        config = load_config()

    fmt = formatter or (
        MarkdownFormatter(formatting_config=config.formatting)
        if for_pdf
        else PlainFormatter(formatting_config=config.formatting)
    )

    week_percentages = {1: "70%", 2: "80%", 3: "90%", 4: "75%", 5: "85%", 6: "95%"}
    weeks = [int(week)] if week and week != "all" else list(range(1, 7))

    lines: list[str] = []
    for w in weeks:
        lines.append(fmt.heading(f"WEEK {w} - {week_percentages[w]}", level=2))
        lines.append("")

        for lift_cfg in lifts:
            lines.append(
                tb.Program.print_exercise(
                    exercise=lift_cfg["exercise"],
                    oneRepMax=lift_cfg["one_rm"],
                    body_weight=lift_cfg.get("body_weight"),
                    bar_weight=lift_cfg.get("bar_weight", 45.0),
                    bar_label=lift_cfg.get("bar_label"),
                    formatter=fmt,
                    week=w,
                    print_1rm=True,
                )
            )
            lines.append("")

        if w != weeks[-1]:
            if for_pdf:
                lines.append(r"\pagebreak")
            else:
                lines.append("")
                lines.append(fmt.horizontal_rule())
                lines.append("")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Output utilities
# ---------------------------------------------------------------------------

def copy_to_clipboard(text: str) -> None:
    """Copy text to system clipboard via pbcopy (macOS). Silent no-op elsewhere."""
    pbcopy = shutil.which("pbcopy")
    if not pbcopy:
        return
    try:
        subprocess.run([pbcopy], input=text.encode("utf-8"), check=True)
    except Exception:
        pass


def default_pdf_path(title: Optional[str]) -> Path:
    """Return ~/Downloads/<sanitised-title>.pdf (dated default if title is None)."""
    if not title:
        title = f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", title).strip("_")
    if not safe.lower().endswith(".pdf"):
        safe += ".pdf"
    return Path.home() / "Downloads" / safe


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _lift_summary_line(lift: dict) -> str:
    """One-line summary for a lift, e.g. 'Squat: 455#' or 'Weighted Pull-Up: 85# added @ BW 212#'."""
    name = format_exercise_name(lift["exercise"])
    one_rm = lift["one_rm"]
    bw = lift.get("body_weight")
    bar_lbl = lift.get("bar_label")
    bar_wt = lift.get("bar_weight", 45.0)

    if bw is not None:
        return f"{name}: {one_rm - bw}# added @ BW {bw}#"

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
