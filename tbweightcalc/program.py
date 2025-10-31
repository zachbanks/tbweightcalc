import os
import pathlib
from dataclasses import dataclass, field

import jinja2
import weasyprint

from tbweightcalc import ExerciseCluster


@dataclass
class Program:
    """Class represents a TB Program which contains a list of exercises to follow over a period of time."""

    title: str  # Tactical Barbell: 2023-01
    exercises: list[ExerciseCluster] = field(default_factory=list)

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
    def print_exercise(cls, exercise, oneRepMax, week="all", body_weight=None):
        """
        Prints an exercise cluster for a given week.
        If no week is provided, then prints out all 6 weeks.
        """
        c = []

        if week == None:
            week = "all"

        if week == "all":
            for i in range(6):
                c.append(
                    ExerciseCluster(
                        week=(i + 1),
                        exercise=exercise,
                        oneRepMax=oneRepMax,
                        body_weight=body_weight,
                    )
                )
        elif int(week) > 0 and int(week) <= 6:
            c.append(
                ExerciseCluster(
                    week=int(week),
                    exercise=exercise,
                    oneRepMax=oneRepMax,
                    body_weight=body_weight,
                )
            )

        print("### %s ###" % (exercise.upper()))

        s = ""
        if body_weight:
            s += "1RM: %d# @ BW of %d#" % ((oneRepMax - body_weight), body_weight)
        else:
            s = "1RM: %s#" % oneRepMax
        print(s)
        print()

        # Print clusters array.
        for x in c:
            print(x)

    @staticmethod
    def calc_1rm(weight: int, reps: int = 1):
        """Calculates 1RM using Brzycki Equation"""
        return round(weight / (1.0278 - (0.0278 * reps)))
