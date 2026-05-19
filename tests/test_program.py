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

        # Should have "SQUAT" but no parenthetical bar info
        assert "SQUAT" in output
        lines = output.split('\n')
        title_line = lines[0]
        assert "SQUAT" in title_line
        assert "(" not in title_line

    def test_custom_bar_weight_no_label_shown_in_title(self):
        """Custom bar weight without label shows weight in title."""
        output = Program.print_exercise(
            exercise="squat",
            oneRepMax=455,
            week=1,
            bar_weight=35.0,
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        # PlainFormatter without config uses "lbs" unit
        assert "SQUAT (35 lbs bar)" in output
        # Should not show decimal point for whole number
        assert "35.0" not in output



    def test_custom_bar_weight_with_multiple_exercises(self):
        """Test different bar weights on different exercises."""
        # Standard bar – no parenthetical
        output1 = Program.print_exercise(
            exercise="deadlift",
            oneRepMax=500,
            week=1,
            bar_weight=45.0,
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        # Custom bar weight, no label
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

        assert "OVERHEAD PRESS (15 lbs bar)" in output2

    def test_custom_bar_weight_all_weeks(self):
        """Custom bar weight should appear in the header when week='all'."""
        output = Program.print_exercise(
            exercise="bench press",
            oneRepMax=315,
            week="all",
            bar_weight=55.0,
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        # One header for the whole exercise block
        assert "BENCH PRESS (55 lbs bar)" in output


class TestPrintExerciseBarLabel:
    """Test that custom bar labels appear correctly in exercise titles."""

    def test_bar_label_with_custom_weight_in_title(self):
        """Label + custom weight: 'EXERCISE (Label - weight)' format."""
        output = Program.print_exercise(
            exercise="zercher squat",
            oneRepMax=300,
            week=1,
            bar_weight=25.0,
            bar_label="Axle Bar",
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        assert "ZERCHER SQUAT (Axle Bar - 25 lbs)" in output

    def test_bar_label_with_standard_weight_in_title(self):
        """Label on a 45# bar: 'EXERCISE (Label)' format."""
        output = Program.print_exercise(
            exercise="squat",
            oneRepMax=455,
            week=1,
            bar_weight=45.0,
            bar_label="Safety Squat Bar",
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        assert "SQUAT (Safety Squat Bar)" in output
        # Should not show weight separately since it's the standard 45
        assert "45 lbs" not in output.split('\n')[0]

    def test_bar_label_in_title_with_custom_weight(self):
        """Bar label + non-standard weight: 'EXERCISE (Label - weight)' format."""
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

    def test_bar_label_trap_bar_deadlift(self):
        """Trap bar deadlift shows label and weight in title."""
        output = Program.print_exercise(
            exercise="deadlift",
            oneRepMax=380,
            week=1,
            bar_weight=60.0,
            bar_label="Trap Bar",
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        assert "DEADLIFT (Trap Bar - 60 lbs)" in output

    def test_bar_label_overrides_weight_only_display(self):
        """When label is given, label+weight format replaces 'weight bar' format."""
        output_with_label = Program.print_exercise(
            exercise="squat",
            oneRepMax=455,
            week=1,
            bar_weight=35.0,
            bar_label="Buffalo Bar",
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        output_no_label = Program.print_exercise(
            exercise="squat",
            oneRepMax=455,
            week=1,
            bar_weight=35.0,
            bar_label=None,
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        assert "SQUAT (Buffalo Bar - 35 lbs)" in output_with_label
        assert "SQUAT (35 lbs bar)" in output_no_label
        # The label version should not use the "bar" indicator
        assert "35 lbs bar" not in output_with_label

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

    def test_bar_label_appears_in_set_warmup_line(self):
        """Bar-only warmup sets show 'Bar' (label only appears in exercise title)."""
        output = Program.print_exercise(
            exercise="zercher squat",
            oneRepMax=300,
            week=1,
            bar_weight=25.0,
            bar_label="Axle Bar",
            print_1rm=False,
            formatter=PlainFormatter(),
        )

        lines = output.split('\n')
        bar_only_lines = [l for l in lines if "2 x 5" in l]
        assert len(bar_only_lines) == 1
        # Individual set lines show "Bar", not the label (label only in title)
        assert "Bar" in bar_only_lines[0]
        assert "Axle Bar" not in bar_only_lines[0]
