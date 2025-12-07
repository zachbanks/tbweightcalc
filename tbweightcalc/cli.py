import argparse
import datetime
import tbweightcalc as tb
from tbweightcalc.program import apply_markdown, markdown_to_pdf
import os
import re
import shutil
import subprocess
from pathlib import Path


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


def default_pdf_path(title: str | None) -> Path:
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

    # If week is specified as single week, use that; if "all" or None, do 1–6.
    if args.week and args.week != "all":
        weeks = [int(args.week)]
    else:
        weeks = list(range(1, 7))

    for week in weeks:
        # Week header
        lines.append(apply_markdown(f"WEEK {week}", "h2"))
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
        "--1rm",
        help="Enter weight lifted and number of reps",
        type=int,
        nargs=2,
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

    args = parser.parse_args()

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
