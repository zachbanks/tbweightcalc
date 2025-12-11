from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass, field
import re

from .formatting import Formatter, PlainFormatter


@dataclass
class Program:
    """Class represents a TB Program which contains a list of exercises to follow over a period of time."""

    title: str  # Tactical Barbell: 2023-01
    exercises: "list[ExerciseCluster]" = field(default_factory=list)

    TEMPLATE_PATH = pathlib.Path.cwd() / "templates"

    @classmethod
    def generate_pdf_from_template(
        cls,
        template_path: pathlib.Path,
        save_path: pathlib.Path,
        target_filename: str,
        **context_objects,
    ) -> pathlib.Path:
        """
        Take jinja template, pass context objects to it, and convert it into html.

        :returns Filepath of created file.
        """
        import jinja2
        import weasyprint

        parent_path = template_path.parent.resolve()
        loader = jinja2.FileSystemLoader(searchpath=parent_path)
        env = jinja2.Environment(loader=loader)

        # Take jinja template and convert it into html.
        template = env.get_template(template_path.name)
        output = template.render(**context_objects)

        # Convert HTML to pdf.

        if not save_path.exists():
            os.makedirs(save_path)

        target_path = save_path / target_filename

        weasyprint.HTML(string=output).write_pdf(target=target_path)

        return target_path

    @classmethod
    def print_exercise(
        cls,
        exercise,
        oneRepMax,
        week="all",
        body_weight=None,
        print_1rm=True,
        formatter: Formatter | None = None,
    ):
        from .exercise_cluster import ExerciseCluster

        """
        Builds and returns an exercise cluster string for a given week.
        If week="all", returns all 6 weeks concatenated.
        """

        output_lines = []  # ← collect output instead of printing
        clusters = []  # ← stores ExerciseCluster objects
        fmt = formatter or PlainFormatter()

        # Build clusters
        if week is None:
            week = "all"

        if week == "all":
            for i in range(6):
                clusters.append(
                    ExerciseCluster(
                        week=i + 1,
                        exercise=exercise,
                        oneRepMax=oneRepMax,
                        body_weight=body_weight,
                        formatter=fmt,
                    )
                )
        elif 1 <= int(week) <= 6:
            clusters.append(
                ExerciseCluster(
                    week=int(week),
                    exercise=exercise,
                    oneRepMax=oneRepMax,
                    body_weight=body_weight,
                    formatter=fmt,
                )
            )
        else:
            raise ValueError("Week must be 1–6 or 'all'")

        # Header
        output_lines.append(fmt.heading(f"{exercise.upper()}", level=3))
        output_lines.append("")  # blank line

        # Optional 1RM line
        if print_1rm:
            if body_weight is not None:
                s = "1RM: %d# @ BW of %d#" % ((oneRepMax - body_weight), body_weight)
            else:
                s = "1RM: %s#" % oneRepMax
            output_lines.append(s)
            output_lines.append("")

        # Cluster strings
        for x in clusters:
            output_lines.append(str(x))

        # Return final string
        return "\n".join(output_lines)

    @staticmethod
    def calc_1rm(weight: int, reps: int = 1):
        """Calculates 1RM using Brzycki Equation"""
        return round(weight / (1.0278 - (0.0278 * reps)))


import datetime
import subprocess
import tempfile
import pathlib


def markdown_to_pdf(md_text: str, output_path: str, title: str | None = None):
    """
    Convert markdown to PDF using pandoc + xelatex.

    - Uses a monospace 'coding' font.
    - Uses Pandoc/LaTeX title (big, centered).
    - Adds footer: left = date, right = page number.
    - Expects page breaks as raw '\\pagebreak' (or '\\newpage') in the markdown.
    - Disables the horizontal rule at the top of each page.
    """
    if not title:
        title = f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"

    footer_date = datetime.date.today().strftime("%Y-%m-%d")

    # This markdown is already tailored for PDF by the caller
    md_for_pdf = md_text.lstrip("\n")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tmp:
        tmp.write(md_for_pdf.encode("utf-8"))
        tmp_path = tmp.name

    title = f"\\Huge\\textbf{{{title}}}"
    cmd = [
        "pandoc",
        "-f",
        "markdown+raw_tex",  # allow \pagebreak / \newpage to pass through
        tmp_path,
        "-o",
        output_path,
        "--pdf-engine=xelatex",
        # Big centered title
        "-V",
        f"title={title}",
        "-V",
        "header-includes=\\usepackage{titling}",
        "-V",
        "header-includes=\\setlength{\\droptitle}{-7em}",
        # Coding-style font + layout
        "-V",
        "mainfont=JetBrainsMono Nerd Font Mono",
        "-V",
        "monofont=JetBrainsMono Nerd Font Mono",
        "-V",
        "fontsize=12pt",
        "-V",
        "geometry:margin=1in",
        # fancyhdr: footer only, no header rule
        "-V",
        "header-includes=\\usepackage{fancyhdr}",
        "-V",
        "header-includes=\\pagestyle{fancy}",
        "-V",
        "header-includes=\\fancyhf{}",  # clear default header/footer
        "-V",
        "header-includes=\\renewcommand{\\headrulewidth}{0pt}",  # ❗ no top line
        # normal pages footer
        "-V",
        f"header-includes=\\fancyfoot[L]{{Generated {footer_date}}}",
        "-V",
        "header-includes=\\fancyfoot[R]{Page \\thepage}",
        # title/plain pages: same footer + no headrule
        "-V",
        (
            "header-includes="
            "\\fancypagestyle{plain}{"
            "\\fancyhf{}"
            "\\renewcommand{\\headrulewidth}{0pt}"
            f"\\fancyfoot[L]{{Generated {footer_date}}}"
            "\\fancyfoot[R]{Page \\thepage}"
            "}"
        ),
    ]

    subprocess.run(cmd, check=True)
    return pathlib.Path(output_path)
