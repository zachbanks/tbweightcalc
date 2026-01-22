import pytest
from tbweightcalc.program import Program
from tbweightcalc.formatting import PlainFormatter


class TestPrintExerciseBarWeight:
    """Test custom bar weight display in exercise titles."""

    def test_standard_bar_weight_not_shown(self):
        """Standard 45# bar should not show weight in title."""
        output = Program.print_exercise(
            exercise="squat",
            oneRepMax=455,
            week=1,
            bar_weight=45.0,
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        # Should have "SQUAT" but not "45# bar" or "(45# bar)"
        assert "SQUAT" in output
        assert "45# bar" not in output
        assert "(45# bar)" not in output
        # Ensure the title line doesn't have parentheses (which would indicate bar weight)
        lines = output.split('\n')
        title_line = lines[0]
        assert "SQUAT" in title_line
        assert "(" not in title_line

    def test_custom_bar_weight_shown_as_integer(self):
        """Custom bar weight that's a whole number should display as integer."""
        output = Program.print_exercise(
            exercise="squat",
            oneRepMax=455,
            week=1,
            bar_weight=35.0,
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        # Should show "SQUAT (35 lbs)" with PlainFormatter
        assert "SQUAT (35 lbs)" in output
        # Should not show decimal point
        assert "35.0" not in output

    def test_custom_bar_weight_shown_as_decimal(self):
        """Custom bar weight with decimal should display with decimal."""
        output = Program.print_exercise(
            exercise="squat",
            oneRepMax=455,
            week=1,
            bar_weight=33.5,
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        # Should show "SQUAT (33.5 lbs)" with PlainFormatter
        assert "SQUAT (33.5 lbs)" in output

    def test_custom_bar_weight_with_multiple_exercises(self):
        """Test different bar weights on different exercises."""
        # Standard bar
        output1 = Program.print_exercise(
            exercise="deadlift",
            oneRepMax=500,
            week=1,
            bar_weight=45.0,
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        # Custom bar
        output2 = Program.print_exercise(
            exercise="overhead press",
            oneRepMax=185,
            week=1,
            bar_weight=15.0,
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        assert "DEADLIFT" in output1
        assert "bar" not in output1.lower()

        assert "OVERHEAD PRESS (15 lbs)" in output2

    def test_custom_bar_weight_all_weeks(self):
        """Custom bar weight should appear in all weeks when week='all'."""
        output = Program.print_exercise(
            exercise="bench press",
            oneRepMax=315,
            week="all",
            bar_weight=55.0,
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        # Should appear multiple times (once per week header)
        assert output.count("BENCH PRESS (55 lbs)") == 6  # One for each of 6 weeks

    def test_bar_label_in_title(self):
        """Bar label should appear in exercise title, not in individual reps."""
        output = Program.print_exercise(
            exercise="squat",
            oneRepMax=315,
            week=1,
            bar_weight=55.0,
            bar_label="Safety Squat Bar",
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        # Label should appear in title with weight: "SQUAT (Safety Squat Bar - 55 lbs)"
        assert "SQUAT (Safety Squat Bar - 55 lbs)" in output

        # Individual bar-only sets should just say "Bar", not include the label
        lines = output.split('\n')
        for line in lines:
            if "x 5 -" in line and "55 lbs" in line:
                # This is the bar-only warmup set
                assert "Bar" in line
                assert "Safety Squat Bar" not in line
                break
        else:
            # Make sure we found the bar-only set
            assert False, "Could not find bar-only warmup set in output"

    def test_bar_label_takes_precedence_over_bar_weight(self):
        """When both bar_label and non-standard bar_weight are provided, label takes precedence in title."""
        output = Program.print_exercise(
            exercise="squat",
            oneRepMax=315,
            week=1,
            bar_weight=55.0,
            bar_label="SSB",
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        # Label should be used in title with weight: "SQUAT (SSB - 55 lbs)"
        assert "SQUAT (SSB - 55 lbs)" in output
