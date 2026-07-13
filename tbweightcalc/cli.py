"""
CLI interface for tbweightcalc.

This module contains argument parsing, interactive prompts, and the main()
entry point. All business logic lives in tbweightcalc.core.
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path

from tbweightcalc.config import Config, load_config
from tbweightcalc.formatting import MarkdownFormatter, PlainFormatter
from tbweightcalc.onerm import calculate_one_rm
from tbweightcalc.program import markdown_to_pdf
from tbweightcalc.sessions import SessionStore

# Re-export everything from core so existing callers (tests, external code)
# that do `from tbweightcalc.cli import X` or `cli.X` keep working.
from tbweightcalc.core import (  # noqa: F401
    INTERACTIVE_LIFT_SLOTS,
    _ADJUSTMENT_PRESETS,
    _apply_lift_adjustment,
    _lift_summary_line,
    build_program_markdown,
    copy_to_clipboard,
    default_pdf_path,
    evaluate_weight_expression,
    format_exercise_name,
    parse_one_rm_string,
    parse_weighted_pullup_string,
)


# ---------------------------------------------------------------------------
# Argparse → lifts conversion
# ---------------------------------------------------------------------------

def _lifts_from_args(args: argparse.Namespace) -> list[dict]:
    """Extract a unified lifts list from a parsed argparse.Namespace."""
    if hasattr(args, "lifts") and args.lifts:
        if isinstance(args.lifts, list):
            return args.lifts
        # dict format (legacy: {exercise_name: {one_rm, body_weight, ...}})
        return [
            {"exercise": ex, **cfg}
            for ex, cfg in args.lifts.items()
        ]

    # Individual CLI flags (--squat, --bench, etc.)
    lifts: list[dict] = []
    for attr, exercise in [
        ("squat",             "squat"),
        ("front_squat",       "front squat"),
        ("zercher_squat",     "zercher squat"),
        ("bench",             "bench press"),
        ("overhead_press",    "overhead press"),
        ("deadlift",          "deadlift"),
        ("zercher_deadlift",  "zercher deadlift"),
        ("trap_bar_deadlift", "trap bar deadlift"),
    ]:
        val = getattr(args, attr, None)
        if val is not None:
            lifts.append({"exercise": exercise, "one_rm": round(val), "body_weight": None, "bar_weight": 45.0})

    wpu = getattr(args, "weighted_pullup", None)
    if wpu is not None:
        one_rm, bw = wpu
        lifts.append({"exercise": "weighted pullup", "one_rm": one_rm, "body_weight": bw, "bar_weight": 45.0})

    return lifts


# ---------------------------------------------------------------------------
# Interactive I/O helpers
# ---------------------------------------------------------------------------

def _prompt_for_exercise_1rm(exercise_name: str, store=None) -> tuple[int | None, float, str | None]:
    """Prompt for a single exercise 1RM and bar info. Returns (one_rm, bar_weight, bar_label)."""
    for slot in INTERACTIVE_LIFT_SLOTS:
        for opt in slot["options"]:
            if opt["exercise_name"] == exercise_name:
                one_rm = prompt_lift_one_rm(opt["prompt"])
                if one_rm is None:
                    return (None, 45.0, None)
                bar_weight, bar_label = prompt_bar_weight(exercise_name, store=store)
                return (one_rm, bar_weight, bar_label)

    generic = f"{format_exercise_name(exercise_name)} 1RM or set (e.g. '225', '200 5', blank to skip): "
    one_rm = prompt_lift_one_rm(generic)
    if one_rm is None:
        return (None, 45.0, None)
    bar_weight, bar_label = prompt_bar_weight(exercise_name, store=store)
    return (one_rm, bar_weight, bar_label)


def _review_and_edit_lifts(lifts: list[dict], store=None) -> list[dict]:
    """Show numbered lift summary and let the user re-enter any entry before continuing."""
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
            added = lift["one_rm"] - bw if bw else lift["one_rm"]
            print(f"\nRe-entering Weighted Pull-Up (current: {added}# added @ BW {bw}#)")

            bw_raw = input(f"Bodyweight in lbs (current {bw}#, blank to keep): ").strip()
            new_bw = bw
            if bw_raw:
                try:
                    new_bw = int(bw_raw)
                except ValueError:
                    print("Invalid bodyweight; keeping current.")

            wpu_raw = input("WPU set (e.g. '35 4', '35x4', blank to keep current): ").strip()
            if wpu_raw:
                est = parse_weighted_pullup_string(new_bw, wpu_raw)
                if est is not None:
                    lifts[idx - 1]["one_rm"] = est
                    lifts[idx - 1]["body_weight"] = new_bw
                    print(f"Updated: {_lift_summary_line(lifts[idx - 1])}")
                else:
                    print("Could not parse WPU input; keeping current values.")
            elif new_bw != bw:
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
    """Prompt for bar weight and optional label. Returns (bar_weight, bar_label)."""
    bars = store.list_bars() if store is not None else []

    while True:
        if bars:
            print("  Saved bars:")
            for i, b in enumerate(bars, start=1):
                w = int(b["weight"]) if b["weight"] == int(b["weight"]) else b["weight"]
                print(f"    [{i}] {b['name']} ({w}#)")

        hint = f"1-{len(bars)} for saved bar, or " if bars else ""
        raw = input(f"Bar weight for {exercise_name} ({hint}default 45): ").strip()

        if not raw:
            return (45.0, None)

        if bars:
            try:
                idx = int(raw)
                if 1 <= idx <= len(bars):
                    b = bars[idx - 1]
                    return (b["weight"], b["name"])
            except ValueError:
                pass

        try:
            bar_weight = float(raw)
            if bar_weight <= 0:
                print("Bar weight must be greater than 0.")
                continue
        except ValueError:
            print("Invalid input. Enter a number or press Enter for default (45).")
            continue

        label = input("Optional label for bar (e.g. 'C-70', blank to skip): ").strip()

        if store is not None and label and bar_weight != 45.0:
            save_raw = input(
                f"Save '{label}' ({int(bar_weight) if bar_weight == int(bar_weight) else bar_weight}#)"
                " as a custom bar for future use? (y/n): "
            ).strip().lower()
            if save_raw in ("y", "yes"):
                store.save_bar(label, bar_weight)
                print(f"[Saved bar '{label}']")

        return (bar_weight, label if label else None)


def prompt_lift_one_rm(label: str) -> int | None:
    """Prompt for a lift 1RM or set; loops until valid or blank. Returns int or None."""
    while True:
        raw = input(
            f"{label} 1RM or set (e.g. '455' or '240 5' or '240x5', blank to skip): "
        )
        stripped = raw.strip()
        if not stripped:
            return None
        value = parse_one_rm_string(stripped)
        if value is not None:
            return value
        print(f"Could not parse input for {label!r}. Try again or leave blank to skip.")


def prompt_weighted_pullup_interactive() -> tuple[int | None, int | None]:
    """Interactive WPU prompt. Returns (one_rep_max_total, bodyweight)."""
    bodyweight: int | None = None
    while True:
        bw_raw = input("Bodyweight for weighted pull-ups (lb, blank to skip WPU): ").strip()
        if not bw_raw:
            return None, None
        try:
            bodyweight = int(bw_raw)
            break
        except ValueError:
            print("Invalid bodyweight. Please enter a whole number or leave blank to skip.")

    while True:
        wpu_raw = input(
            "Weighted pull-up set (additional weight and reps). Examples:\n"
            "  '35 4'   -> +35 lb for 4 reps\n"
            "  '35x4'   -> +35 lb for 4 reps\n"
            "  '45'     -> +45 lb for 1 rep\n"
            "  '0 4'    -> bodyweight-only for 4 reps\n"
            "  'bw 4'   -> bodyweight-only for 4 reps\n"
            "Blank to skip WPU: "
        )
        stripped = wpu_raw.strip()
        if not stripped:
            return None, bodyweight
        one_rm = parse_weighted_pullup_string(bodyweight, stripped)
        if one_rm is not None:
            return one_rm, bodyweight
        print("Could not parse weighted pull-up input. Try again or leave blank to skip.")


def prompt_one_rm() -> None:
    """Interactive 1RM estimator (Epley). Prints result and copies to clipboard."""
    print("=== 1RM Estimator (Epley) ===")
    try:
        weight = float(input("Enter weight lifted (in pounds): ").strip())
        reps = int(input("Enter number of reps: ").strip())
        est = calculate_one_rm(weight, reps)
        print(f"\nEstimated 1RM: {est} lb")
        copy_to_clipboard(str(est))
    except ValueError as e:
        print(f"\nInvalid input: {e}")
    except KeyboardInterrupt:
        print("\n[Aborted by user]")


def _prompt_save_session(lifts: list[dict], store: SessionStore, default_name: str | None = None) -> None:
    """After generating a program, offer to save the lifts as a named session."""
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


def _prompt_adjustment(lifts: list[dict]) -> list[dict]:
    """Offer preset or custom % adjustment to 1RM values, globally or per-exercise."""
    print("\nAdjust 1RMs:")
    labels = "  ".join(f"[{i}] {label}" for i, (label, _) in enumerate(_ADJUSTMENT_PRESETS, 1))
    print(f"  {labels}  [7] Custom")
    raw = input("Choice (Enter to skip): ").strip()
    if not raw:
        return lifts

    pct: float | None = None
    if raw.isdigit() and 1 <= int(raw) <= 6:
        pct = _ADJUSTMENT_PRESETS[int(raw) - 1][1]
    elif raw == "7":
        custom = input("Enter % (e.g. 7.5 or -3): ").strip()
        try:
            pct = float(custom)
        except ValueError:
            print("Invalid percentage; skipping adjustment.")
            return lifts
    else:
        try:
            pct = float(raw)
        except ValueError:
            print("Invalid choice; skipping adjustment.")
            return lifts

    exercises = [l["exercise"] for l in lifts]
    print("\nApply to:")
    print("  [Enter] All lifts")
    for i, ex in enumerate(exercises, 1):
        print(f"  [{i}] {format_exercise_name(ex)} (1RM: {lifts[i - 1].get('one_rm')})")
    scope = input("Choice (Enter for all): ").strip()

    exercise: str | None = None
    if scope:
        try:
            idx = int(scope)
            if 1 <= idx <= len(exercises):
                exercise = exercises[idx - 1]
        except ValueError:
            for ex in exercises:
                if scope.lower() in ex.lower():
                    exercise = ex
                    break

    adjusted = _apply_lift_adjustment(lifts, pct, exercise)
    print(f"[Applied {pct:+.4g}% to {'all lifts' if exercise is None else repr(exercise)}]")
    return adjusted


def _print_sessions(sessions: list[dict]) -> None:
    if not sessions:
        print("  (no saved sessions)")
        return
    for i, s in enumerate(sessions, start=1):
        date = s.get("updated") or s["created"]
        print(f"  [{i}] {s['name']}  ({date})  id:{s['id']}")


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def run_interactive() -> None:
    """Full interactive mode: select template, enter lifts, generate output."""
    print("Tactical Barbell Max Strength - Interactive Mode\n")

    store = SessionStore()
    lifts: list[dict] = []
    loaded_from_session = False
    loaded_session_name: str | None = None

    while True:
        sessions = store.list_sessions()
        if not sessions:
            break
        print("Saved sessions:")
        _print_sessions(sessions)
        load_raw = input(
            "\nLoad a session (number/name), 'del <number/name>' to delete, or Enter to start fresh: "
        ).strip()
        if not load_raw:
            break
        if load_raw.lower().startswith("del "):
            target = load_raw[4:].strip()
            victim = store.load_session(target)
            if victim:
                store.delete_session(victim["id"])
                print(f"[Deleted '{victim['name']}']")
            else:
                print(f"No session found for '{target}'.")
        else:
            session = store.load_session(load_raw)
            if session:
                lifts = [dict(lift) for lift in session["lifts"]]
                loaded_from_session = True
                loaded_session_name = session["name"]
                print(f"[Loaded '{session['name']}']")
            else:
                print(f"No session found for '{load_raw}'; starting fresh.")
            break

    skip_save = False
    if loaded_from_session:
        mode = input("\nEdit, duplicate, or output? [e/d/o, default o]: ").strip().lower()
        if mode == "e":
            raw_title = input(f"\nProgram title (Enter for '{loaded_session_name}'): ").strip()
            title = raw_title if raw_title else loaded_session_name
            lifts = _review_and_edit_lifts(lifts, store=store)
        elif mode == "d":
            default_dup_title = f"Copy of {loaded_session_name}"
            raw_title = input(f"\nProgram title (Enter for '{default_dup_title}'): ").strip()
            title = raw_title if raw_title else default_dup_title
            lifts = _prompt_adjustment(lifts)
            lifts = _review_and_edit_lifts(lifts, store=store)
        else:
            title = loaded_session_name
            skip_save = True
    else:
        raw_title = input("\nProgram title (leave blank for default): ").strip()
        title = raw_title or f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"
        lifts = []

        print("\nSelect template:")
        print("  [1] Classic: Squat / Bench / Deadlift / Weighted Pull-Up")
        print("  [2] Front-Squat Block: Front Squat / Overhead Press / Deadlift / Weighted Pull-Up")
        print("  [3] Zercher Block: Zercher Squat / Bench Press / Deadlift / Weighted Pull-Up")
        print("  [4] Custom: choose lifts manually")
        template_choice = input("Template [1/2/3/4, default 1]: ").strip()
        if template_choice not in ("1", "2", "3", "4"):
            template_choice = "1"

        if template_choice in ("1", "2", "3"):
            preset_map = {
                "1": ["squat", "bench press", "deadlift"],
                "2": ["front squat", "overhead press", "deadlift"],
                "3": ["zercher squat", "bench press", "deadlift"],
            }
            for ex_name in preset_map[template_choice]:
                one_rm, bar_weight, bar_label = _prompt_for_exercise_1rm(ex_name, store=store)
                if one_rm is not None:
                    lifts.append({
                        "exercise": ex_name, "one_rm": one_rm,
                        "body_weight": None, "bar_weight": bar_weight, "bar_label": bar_label,
                    })
        else:
            for slot in INTERACTIVE_LIFT_SLOTS:
                print(f"\n{slot['name']}:")
                for idx, opt in enumerate(slot["options"], start=1):
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
                    if not (1 <= idx <= len(slot["options"])):
                        print("Invalid option number. Try again.")
                        continue

                    selected = slot["options"][idx - 1]
                    one_rm = prompt_lift_one_rm(selected["prompt"])
                    if one_rm is None:
                        print("No valid 1RM entered; skipping.")
                        break
                    bar_weight, bar_label = prompt_bar_weight(selected["exercise_name"], store=store)
                    lifts.append({
                        "exercise": selected["exercise_name"], "one_rm": one_rm,
                        "body_weight": None, "bar_weight": bar_weight, "bar_label": bar_label,
                    })
                    break

        # Weighted pull-up
        bw_raw = input("\nBodyweight for weighted pull-ups (lb, blank to skip WPU): ").strip()
        if bw_raw:
            try:
                bodyweight = int(bw_raw)
            except ValueError:
                print("Could not parse bodyweight; skipping weighted pull-ups.")
                bodyweight = None
            if bodyweight is not None:
                while True:
                    wpu_raw = input(
                        "Weighted pull-up set (e.g. '35 4', '35x4', 'bw 4', blank to skip): "
                    ).strip()
                    if not wpu_raw:
                        break
                    est = parse_weighted_pullup_string(bodyweight, wpu_raw)
                    if est is None:
                        print("Could not parse that set. Try again (or press Enter to skip).")
                        continue
                    lifts.append({
                        "exercise": "weighted pullup", "one_rm": est,
                        "body_weight": bodyweight, "bar_weight": 45.0,
                    })
                    break

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
                            wpu_1rm, bw = prompt_weighted_pullup_interactive()
                            if wpu_1rm is None:
                                print("No valid WPU data; skipping.")
                                break
                            lifts.append({"exercise": ex_name, "one_rm": wpu_1rm, "body_weight": bw, "bar_weight": 45.0})
                        else:
                            one_rm, bar_weight, bar_label = _prompt_for_exercise_1rm(ex_name, store=store)
                            if one_rm is None:
                                print("No valid 1RM entered; skipping.")
                                break
                            lifts.append({"exercise": ex_name, "one_rm": one_rm, "body_weight": None, "bar_weight": bar_weight, "bar_label": bar_label})
                        print(f"Added {format_exercise_name(ex_name)}.")
                        break

                    if input("\nAdd another exercise? (y/n, default n): ").strip().lower() not in ("y", "yes"):
                        break

        lifts = _review_and_edit_lifts(lifts, store=store)

    week = input("\nWeek (1–6 or 'all', default 'all'): ").strip().lower() or "all"
    out_mode = input("Output: [t]ext, [p]df, [b]oth (default b): ").strip().lower()
    if out_mode not in ("t", "p", "b"):
        out_mode = "b"

    screen_output = f"# {title}\n\n{build_program_markdown(lifts, week=week, for_pdf=False)}"

    if out_mode in ("t", "b"):
        print(screen_output)
        print()
        copy_to_clipboard(screen_output)

    if out_mode in ("p", "b"):
        pdf_body = build_program_markdown(lifts, week=week, for_pdf=True)
        pdf_path = default_pdf_path(title)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_to_pdf(pdf_body, str(pdf_path), title=title)
        print(f"\n[PDF saved to: {pdf_path}]")

    if not skip_save:
        _prompt_save_session(lifts, store, default_name=title)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculates Tactical Barbell weight progression for getting swole."
    )

    parser.add_argument("-w", "--week", type=str, nargs="?", const="all",
                        help='Week to print (1–6 or "all")')
    parser.add_argument("-sq", "--squat", type=float, help="1RM for Squat")
    parser.add_argument("-fsq", "--front-squat", type=float, dest="front_squat",
                        help="1RM for Front Squat")
    parser.add_argument("-zsq", "--zercher-squat", type=float, dest="zercher_squat",
                        help="1RM for Zercher Squat")
    parser.add_argument("-bp", "--bench", type=float, help="1RM for Bench Press")
    parser.add_argument("-ohp", "--overhead-press", type=float, dest="overhead_press",
                        help="1RM for Overhead Press")
    parser.add_argument("-dl", "--deadlift", type=float, help="1RM for Deadlift")
    parser.add_argument("-zdl", "--zercher-deadlift", type=float, dest="zercher_deadlift",
                        help="1RM for Zercher Deadlift")
    parser.add_argument("-tbdl", "--trap-bar-deadlift", type=float, dest="trap_bar_deadlift",
                        help="1RM for Trap Bar Deadlift")
    parser.add_argument("-wpu", "--weighted-pullup", type=int, nargs=2,
                        help='1RM and bodyweight for Weighted Pull-Up: "-wpu 245 200"')
    parser.add_argument("-1rm", "--onerepmax", type=int, nargs="*", dest="onerm",
                        help="Estimate 1RM: 'weight reps' or interactively with no args")
    parser.add_argument("--title", help="Program/PDF title")
    parser.add_argument("--pdf", help="Explicit PDF output path")
    parser.add_argument("--config", type=Path,
                        help="Path to custom config YAML (default: ~/.config/tbcalc/config.yaml)")

    session_group = parser.add_argument_group("session management")
    session_group.add_argument("--list-sessions", action="store_true",
                               help="List all saved sessions and exit")
    session_group.add_argument("--load-session", metavar="NAME",
                               help="Load a saved session and generate the program")
    session_group.add_argument("--delete-session", metavar="NAME",
                               help="Delete a saved session and exit")
    session_group.add_argument("--save-session", metavar="NAME",
                               help="Save the current lifts as a named session after generating")

    bar_group = parser.add_argument_group("custom bar management")
    bar_group.add_argument("--list-bars", action="store_true",
                           help="List all saved custom bars and exit")
    bar_group.add_argument("--save-bar", nargs=2, metavar=("NAME", "WEIGHT"),
                           help='Save a custom bar: --save-bar "Trap Bar" 60')
    bar_group.add_argument("--delete-bar", metavar="NAME",
                           help="Delete a saved custom bar by name and exit")

    if len(sys.argv) == 1:
        from tbweightcalc.tui import run_tui
        run_tui()
        return

    args = parser.parse_args()
    config = load_config(args.config if hasattr(args, "config") and args.config else None)
    store = SessionStore()

    # Bar management
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
            print(f"Invalid weight '{weight_str}'.")
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

    # Session management
    if args.list_sessions:
        sessions = store.list_sessions()
        _print_sessions(sessions)
        return

    if args.delete_session:
        if store.delete_session(args.delete_session):
            print(f"Deleted session '{args.delete_session}'.")
        else:
            print(f"No session found for '{args.delete_session}'.")
        return

    if args.load_session:
        session = store.load_session(args.load_session)
        if session is None:
            print(f"No session found for '{args.load_session}'.")
            return
        args.lifts = session["lifts"]
        print(f"[Loaded session '{session['name']}']")

    # 1RM calculator
    if args.onerm is not None:
        if len(args.onerm) == 0:
            prompt_one_rm()
        elif len(args.onerm) == 2:
            est = calculate_one_rm(*args.onerm)
            print(f"Estimated 1RM: {est} lb")
            copy_to_clipboard(str(est))
        else:
            print("Error: --onerepmax expects no args or exactly two (weight reps).")
        return

    title = args.title or f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"
    week = args.week or "all"
    lifts = _lifts_from_args(args)

    screen_formatter = PlainFormatter(formatting_config=config.formatting)
    pdf_formatter = MarkdownFormatter(formatting_config=config.formatting)

    screen_body = build_program_markdown(lifts, week=week, for_pdf=False,
                                         formatter=screen_formatter, config=config)
    screen_output = f"{screen_formatter.heading(title, level=1)}\n\n{screen_body}"
    print(screen_output)

    if config.output.copy_to_clipboard:
        copy_to_clipboard(screen_output)

    pdf_body = build_program_markdown(lifts, week=week, for_pdf=True,
                                      formatter=pdf_formatter, config=config)

    pdf_path = Path(os.path.expanduser(args.pdf)) if args.pdf else default_pdf_path(title)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_to_pdf(pdf_body, str(pdf_path), title=title)
    print(f"\n[PDF saved to: {pdf_path}]")

    if args.save_session:
        lifts_list = lifts if lifts else []
        if lifts_list:
            session = store.save_session(args.save_session, lifts_list)
            action = "Updated" if "updated" in session else "Saved"
            print(f"[{action} session '{session['name']}' ({session['id']})]")


if __name__ == "__main__":
    main()
