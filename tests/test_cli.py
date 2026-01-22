import argparse
from pathlib import Path
import sys
import builtins

import pytest

from tbweightcalc import cli


# -------------------------------------------------------------------
# Tests for format_exercise_name
# -------------------------------------------------------------------


def test_format_exercise_name_rdl():
    """Test that RDL is capitalized properly."""
    assert cli.format_exercise_name("rdl") == "RDL"
    assert cli.format_exercise_name("RDL") == "RDL"
    assert cli.format_exercise_name("Rdl") == "RDL"


def test_format_exercise_name_regular():
    """Test that regular exercises use title case."""
    assert cli.format_exercise_name("squat") == "Squat"
    assert cli.format_exercise_name("bench press") == "Bench Press"
    assert cli.format_exercise_name("front squat") == "Front Squat"


def test_rdl_in_hinge_slot():
    """Test that RDL is available in the Hinge slot."""
    hinge_slot = None
    for slot in cli.INTERACTIVE_LIFT_SLOTS:
        if slot["name"] == "Hinge":
            hinge_slot = slot
            break

    assert hinge_slot is not None, "Hinge slot should exist"

    # Check that RDL is in the options
    rdl_option = None
    for opt in hinge_slot["options"]:
        if opt["exercise_name"] == "rdl":
            rdl_option = opt
            break

    assert rdl_option is not None, "RDL should be in Hinge options"
    assert rdl_option["key"] == "rdl"
    assert "RDL" in rdl_option["prompt"], "Prompt should use capitalized RDL"


# -------------------------------------------------------------------
# Small helper for build_program_markdown tests
# -------------------------------------------------------------------


def make_args(
    week: str | None = "1",
    squat: int | None = 455,
    bench: int | None = 250,
    deadlift: int | None = 300,
    weighted_pullup: tuple[int, int] | None = (252, 210),
    title: str | None = "Test Program",
    pdf: str | None = None,
) -> argparse.Namespace:
    """
    Helper to create an argparse-like Namespace for build_program_markdown.
    Uses the legacy fields that build_program_markdown still understands.
    """
    ns = argparse.Namespace()
    ns.week = week
    ns.squat = squat
    ns.bench = bench
    ns.deadlift = deadlift
    ns.weighted_pullup = list(weighted_pullup) if weighted_pullup else None
    ns.onerm = None
    ns.title = title
    ns.pdf = pdf
    return ns


# -------------------------------------------------------------------
# Tests for helper functions
# -------------------------------------------------------------------


def test_default_pdf_path_with_title(monkeypatch, tmp_path):
    # Make HOME point to a temporary directory so the path is predictable
    fake_home = tmp_path
    monkeypatch.setenv("HOME", str(fake_home))

    path = cli.default_pdf_path("My Cool Program")
    # Should live in ~/Downloads
    assert path.parent == fake_home / "Downloads"
    # Filename should be sanitized and end in .pdf
    assert path.name.startswith("My_Cool_Program")
    assert path.suffix == ".pdf"


def test_default_pdf_path_adds_pdf_extension(monkeypatch, tmp_path):
    fake_home = tmp_path
    monkeypatch.setenv("HOME", str(fake_home))

    path = cli.default_pdf_path("NoExtensionTitle")
    assert path.suffix == ".pdf"


def test_build_program_markdown_single_week_screen():
    args = make_args(week="2")  # only week 2
    md = cli.build_program_markdown(args, for_pdf=False)

    # Should include a WEEK 2 header as an H2
    assert "WEEK 2 - 80%" in md
    # Should not contain PDF-only pagebreak markers
    assert "\\pagebreak" not in md


def test_build_program_markdown_pdf_uses_pagebreaks():
    # This uses "all" weeks so there will be separators
    args = make_args(week="all")
    md = cli.build_program_markdown(args, for_pdf=True)

    # In PDF mode we expect raw \pagebreak between weeks
    assert "\\pagebreak" in md
    # We don't expect visible '---' HRs from our HR helper in PDF mode
    assert "---" not in md


# -------------------------------------------------------------------
# Tests for main() CLI behavior (non-interactive paths)
# -------------------------------------------------------------------


def test_main_prints_title_and_calls_markdown_to_pdf(monkeypatch, capsys, tmp_path):
    """
    Test the full CLI main() without actually generating a PDF or hitting pbcopy.
    """

    # Fake arguments as if called from command line:
    # tbcalc -dl 300 -sq 455 -bp 250 -wpu 252 210 --title "CLI Test" --pdf <tmp_path>
    pdf_path = tmp_path / "cli_test.pdf"
    argv = [
        "tbcalc",
        "-dl",
        "300",
        "-sq",
        "455",
        "-bp",
        "250",
        "-wpu",
        "252",
        "210",
        "--title",
        "CLI Test",
        "--pdf",
        str(pdf_path),
    ]

    # Avoid real clipboard and keep argparse/os/Path in module
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)
    monkeypatch.setattr(sys, "argv", argv)

    # Capture the args passed into markdown_to_pdf instead of actually running it
    called = {}

    def fake_markdown_to_pdf(markdown: str, output_path: str, title: str | None = None):
        called["markdown"] = markdown
        called["output_path"] = output_path
        called["title"] = title

        # Simulate creating a file so tests can assert existence if desired
        Path(output_path).write_bytes(b"%PDF-FAKE%")

    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)

    cli.main()

    # Check stdout
    captured = capsys.readouterr()
    stdout = captured.out

    assert "CLI Test" in stdout
    assert "[PDF saved to:" in stdout

    # Verify markdown_to_pdf was called with expected title and path
    assert called["title"] == "CLI Test"
    assert Path(called["output_path"]) == pdf_path
    assert pdf_path.exists()
    assert called["markdown"]  # non-empty markdown content


def test_main_uses_default_title_when_not_provided(monkeypatch, capsys, tmp_path):
    """
    When --title is not passed, main() should use the default
    'Tactical Barbell Max Strength: YYYY-MM-DD'.
    """
    pdf_path = tmp_path / "no_title.pdf"
    argv = [
        "tbcalc",
        "-dl",
        "300",
        "-sq",
        "455",
        "-bp",
        "250",
        "-wpu",
        "252",
        "210",
        "--pdf",
        str(pdf_path),
    ]

    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)
    monkeypatch.setattr(sys, "argv", argv)

    called = {}

    def fake_markdown_to_pdf(markdown: str, output_path: str, title: str | None = None):
        called["markdown"] = markdown
        called["output_path"] = output_path
        called["title"] = title
        Path(output_path).write_bytes(b"%PDF-FAKE%")

    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)

    cli.main()

    captured = capsys.readouterr()
    stdout = captured.out

    # Should print a heading that starts with the default title
    assert "Tactical Barbell Max Strength:" in stdout

    assert called["title"] is not None
    assert called["title"].startswith("Tactical Barbell Max Strength:")
    assert Path(called["output_path"]) == pdf_path
    assert pdf_path.exists()


def test_main_calls_run_interactive_when_no_args(monkeypatch):
    """
    When tbcalc is run with no CLI arguments (other than the program name),
    main() should call run_interactive() instead of parsing flags.
    """
    called = {"run_interactive": False}

    def fake_run_interactive():
        called["run_interactive"] = True

    # Pretend we invoked "tbcalc" with no extra args
    monkeypatch.setattr(cli, "run_interactive", fake_run_interactive)
    monkeypatch.setattr(sys, "argv", ["tbcalc"])

    cli.main()

    assert called["run_interactive"] is True


# -------------------------------------------------------------------
# Tests for 1RM prompt / helpers
# -------------------------------------------------------------------


def test_prompt_one_rm(monkeypatch, capsys):
    inputs = iter(["275", "5"])

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr(builtins, "input", fake_input)
    # avoid real clipboard
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)

    cli.prompt_one_rm()

    out = capsys.readouterr().out
    assert "Estimated 1RM" in out
    # With Epley & rounding you’ve been using: 275 * (1 + 5/30) = 275 * 7/6 ≈ 321
    assert "321" in out


def test_prompt_one_rm_copies_numeric_result_to_clipboard(monkeypatch, capsys):
    """
    prompt_one_rm should:
      - read weight & reps from input()
      - print the estimated 1RM
      - copy ONLY the numeric 1RM to the clipboard
    """

    # Simulate user typing: weight=275, reps=5
    inputs = iter(["275", "5"])

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr(builtins, "input", fake_input)

    copied = {}

    def fake_copy(text: str) -> None:
        copied["value"] = text

    # Avoid touching the real clipboard
    monkeypatch.setattr(cli, "copy_to_clipboard", fake_copy)

    # Run the prompt
    cli.prompt_one_rm()

    out = capsys.readouterr().out

    # 275 x 5 with your Epley + rounding logic -> 321 lb
    assert "Estimated 1RM" in out
    assert "321 lb" in out

    # Clipboard should contain ONLY the number "321"
    assert copied["value"] == "321"


# -------------------------------------------------------------------
# Tests for parse_one_rm_string
# -------------------------------------------------------------------


class TestParseOneRmString:
    def test_blank_returns_none(self):
        assert cli.parse_one_rm_string("") is None
        assert cli.parse_one_rm_string("   ") is None

    def test_single_integer_treated_as_known_1rm(self):
        assert cli.parse_one_rm_string("455") == 455
        assert cli.parse_one_rm_string("  300  ") == 300

    def test_weight_and_reps_space_separated(self):
        # 240 x 5 -> Epley: 240 * (1 + 5/30) = 240 * 7/6 = 280
        result = cli.parse_one_rm_string("240 5")
        assert result == 280

    def test_weight_and_reps_with_x_separator(self):
        # 240x5 -> 280 as above
        assert cli.parse_one_rm_string("240x5") == 280
        assert cli.parse_one_rm_string("240X5") == 280

    def test_invalid_input_returns_none(self):
        assert cli.parse_one_rm_string("abc") is None
        assert cli.parse_one_rm_string("240 x") is None
        assert cli.parse_one_rm_string("240 5 3") is None

    def test_reps_with_x_separator_and_spaces(self):
        # Base expectation using '240x5'
        base = cli.parse_one_rm_string("240x5")
        assert base is not None

        # Variants that should behave identically
        assert cli.parse_one_rm_string("240 x5") == base
        assert cli.parse_one_rm_string("240x 5") == base
        assert cli.parse_one_rm_string("240 x 5") == base

    def test_decimal_weights_rounded(self):
        # Decimal 1RM values should be rounded to nearest int
        assert cli.parse_one_rm_string("255.6") == 256
        assert cli.parse_one_rm_string("255.4") == 255
        assert cli.parse_one_rm_string("255.5") == 256  # Python rounds to even, but close enough

        # Decimal weights with reps
        # 240.5 x 5 -> Epley: 240.5 * (1 + 5/30) = 240.5 * 7/6 ≈ 280.583 -> 281
        assert cli.parse_one_rm_string("240.5 5") == 281
        assert cli.parse_one_rm_string("240.5x5") == 281

    def test_math_expression_percentage_addition(self):
        # 240 + 10% -> 240 + 24 = 264
        assert cli.parse_one_rm_string("240 + 10%") == 264
        assert cli.parse_one_rm_string("240+10%") == 264
        assert cli.parse_one_rm_string("240 +10%") == 264
        assert cli.parse_one_rm_string("240+ 10%") == 264

    def test_math_expression_percentage_subtraction(self):
        # 240 - 5% -> 240 - 12 = 228
        assert cli.parse_one_rm_string("240 - 5%") == 228
        assert cli.parse_one_rm_string("240-5%") == 228
        assert cli.parse_one_rm_string("240 -5%") == 228
        assert cli.parse_one_rm_string("240- 5%") == 228

    def test_math_expression_absolute_addition(self):
        # 240 + 20 -> 260
        assert cli.parse_one_rm_string("240 + 20") == 260
        assert cli.parse_one_rm_string("240+20") == 260
        # With 'lbs' suffix
        assert cli.parse_one_rm_string("240 + 20 lbs") == 260
        assert cli.parse_one_rm_string("240+20lbs") == 260
        assert cli.parse_one_rm_string("240 + 20 lb") == 260

    def test_math_expression_absolute_subtraction(self):
        # 240 - 10 -> 230
        assert cli.parse_one_rm_string("240 - 10") == 230
        assert cli.parse_one_rm_string("240-10") == 230
        # With 'lbs' suffix
        assert cli.parse_one_rm_string("240 - 10 lbs") == 230
        assert cli.parse_one_rm_string("240-10lbs") == 230
        assert cli.parse_one_rm_string("240 - 10 lb") == 230

    def test_math_expression_with_decimals(self):
        # 240.5 + 10% -> 240.5 + 24.05 = 264.55 -> 265
        assert cli.parse_one_rm_string("240.5 + 10%") == 265
        # 240 + 5.5 -> 245.5 -> 246
        assert cli.parse_one_rm_string("240 + 5.5") == 246
        # 240 - 2.3% -> 240 - 5.52 = 234.48 -> 234
        assert cli.parse_one_rm_string("240 - 2.3%") == 234

    def test_math_expression_edge_cases(self):
        # Large percentage
        assert cli.parse_one_rm_string("200 + 50%") == 300
        # Small percentage
        assert cli.parse_one_rm_string("100 + 1%") == 101
        # Subtraction that results in lower value
        assert cli.parse_one_rm_string("300 - 100") == 200


# -------------------------------------------------------------------
# Tests for parse_weighted_pullup_string + interactive WPU helper
# -------------------------------------------------------------------


class TestParseWeightedPullupString:
    def test_blank_and_whitespace_return_none(self):
        assert cli.parse_weighted_pullup_string(200, "") is None
        assert cli.parse_weighted_pullup_string(200, "   ") is None

    def test_numeric_two_part_and_x_style(self):
        bw = 200

        # '35 4'  -> +35 for 4 reps  => 235 x 4
        r1 = cli.parse_weighted_pullup_string(bw, "35 4")
        # Epley: 235 * (1 + 4/30) ≈ 266
        assert r1 == 266

        # '35x4'  -> +35 for 4 reps  => 235 x 4
        r2 = cli.parse_weighted_pullup_string(bw, "35x4")
        assert r2 == 266

        # '35X4'  -> case-insensitive
        r3 = cli.parse_weighted_pullup_string(bw, "35X4")
        assert r3 == 266

    def test_bw_shorthands(self):
        bw = 200

        # 'bw' -> bodyweight for 1 rep => 200
        r1 = cli.parse_weighted_pullup_string(bw, "bw")
        assert r1 == 200

        # 'bw 4' -> BW for 4 reps => 200 x 4
        r2 = cli.parse_weighted_pullup_string(bw, "bw 4")
        # 200 * (1 + 4/30) ≈ 227
        assert r2 == 227

        # 'bwx4' -> BW for 4 reps
        r3 = cli.parse_weighted_pullup_string(bw, "bwx4")
        assert r3 == 227

        # 'bw x 4' with a space before x
        r4 = cli.parse_weighted_pullup_string(bw, "bw x 4")
        assert r4 == 227

    def test_zero_added_weight(self):
        bw = 200

        # '0 4' -> bodyweight-only for 4 reps
        r = cli.parse_weighted_pullup_string(bw, "0 4")
        # same as bw 4
        assert r == 227

    def test_single_number_means_one_rep_added_weight(self):
        """
        '45' should be interpreted as +45 lb for 1 rep.
        For bodyweight 200:
          total = 245 x 1 -> estimated 1RM should be 245.
        """
        bw = 200
        r = cli.parse_weighted_pullup_string(bw, "45")
        assert r == 245

    def test_invalid_strings_return_none(self):
        bw = 200
        assert cli.parse_weighted_pullup_string(bw, "foo") is None
        assert cli.parse_weighted_pullup_string(bw, "35x") is None
        assert cli.parse_weighted_pullup_string(bw, "x4") is None
        assert cli.parse_weighted_pullup_string(bw, "35 4 x") is None

    def test_numeric_x_separator_with_spaces(self):
        bw = 200

        base = cli.parse_weighted_pullup_string(bw, "35x4")
        assert base is not None

        assert cli.parse_weighted_pullup_string(bw, "35 x4") == base
        assert cli.parse_weighted_pullup_string(bw, "35x 4") == base
        assert cli.parse_weighted_pullup_string(bw, "35 x 4") == base

    def test_decimal_added_weights_rounded(self):
        bw = 200

        # Decimal added weight for 1 rep: 200 + 45.5 = 245.5 x 1 -> 246
        assert cli.parse_weighted_pullup_string(bw, "45.5") == 246

        # Decimal added weight with reps: (200 + 35.5) x 4 = 235.5 x 4
        # Epley: 235.5 * (1 + 4/30) ≈ 266.9 -> 267
        assert cli.parse_weighted_pullup_string(bw, "35.5 4") == 267
        assert cli.parse_weighted_pullup_string(bw, "35.5x4") == 267


class TestPromptWeightedPullupInteractive:
    def test_reprompts_on_invalid_bodyweight_then_skip(self, monkeypatch, capsys):
        """
        If bodyweight input is invalid, it should reprompt until valid or blank.
        Here:
          1) 'abc'  -> invalid
          2) ''     -> skip entirely -> returns (None, None)
        """
        inputs = iter(["abc", ""])

        def fake_input(prompt: str = "") -> str:
            return next(inputs)

        monkeypatch.setattr(builtins, "input", fake_input)

        one_rm, bw = cli.prompt_weighted_pullup_interactive()
        out = capsys.readouterr().out

        assert "Invalid bodyweight" in out
        assert one_rm is None
        assert bw is None

    def test_valid_bodyweight_then_blank_wpu_skips_set(self, monkeypatch, capsys):
        """
        If bodyweight is valid but WPU set input is blank, we should return
        (None, bodyweight).
        """
        inputs = iter(["200", ""])

        def fake_input(prompt: str = "") -> str:
            return next(inputs)

        monkeypatch.setattr(builtins, "input", fake_input)

        one_rm, bw = cli.prompt_weighted_pullup_interactive()

        # No WPU performance, but we know bodyweight
        assert one_rm is None
        assert bw == 200

    def test_invalid_wpu_input_reprompts_until_valid(self, monkeypatch, capsys):
        """
        If bodyweight is valid but the WPU string is invalid,
        the function should reprompt until valid or blank.
        """
        # Inputs:
        #   1) '200'     -> valid bodyweight
        #   2) 'foobar'  -> invalid WPU string
        #   3) '35 4'    -> +35 lb for 4 reps
        inputs = iter(["200", "foobar", "35 4"])

        def fake_input(prompt: str = "") -> str:
            return next(inputs)

        monkeypatch.setattr(builtins, "input", fake_input)

        one_rm, bw = cli.prompt_weighted_pullup_interactive()
        out = capsys.readouterr().out

        # bodyweight should be recorded
        assert bw == 200

        # 35 4 -> total 235 x 4 -> 266 as above
        assert one_rm == 266

        assert "Could not parse weighted pull-up input" in out

    def test_accepts_single_number_as_one_rep_in_interactive(self, monkeypatch, capsys):
        """
        Ensure that the interactive helper also supports the '45' shorthand
        (extra 45 for 1 rep).
        """
        # Inputs:
        #   1) '200' -> bodyweight
        #   2) '45'  -> +45 x 1
        inputs = iter(["200", "45"])

        def fake_input(prompt: str = "") -> str:
            return next(inputs)

        monkeypatch.setattr(builtins, "input", fake_input)

        one_rm, bw = cli.prompt_weighted_pullup_interactive()

        assert bw == 200
        assert one_rm == 245  # 200 + 45 for 1 rep


# -------------------------------------------------------------------
# Fixtures + tests for interactive templates (run_interactive)
# -------------------------------------------------------------------


@pytest.fixture
def no_side_effects(monkeypatch):
    """
    Disable clipboard + PDF side effects, and capture args passed into
    build_program_markdown for inspection.
    """
    captured = {}

    def fake_copy_to_clipboard(_text: str) -> None:
        return

    def fake_markdown_to_pdf(_md: str, _path: str, title: str | None = None) -> None:
        return

    def fake_build_program_markdown(
        args: argparse.Namespace, for_pdf: bool = False
    ) -> str:
        captured["args"] = args
        return "# TEST PROGRAM"

    monkeypatch.setattr(cli, "copy_to_clipboard", fake_copy_to_clipboard)
    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)
    monkeypatch.setattr(cli, "build_program_markdown", fake_build_program_markdown)

    return captured


def test_interactive_template_classic_builds_expected_lifts(
    monkeypatch, no_side_effects
):
    """
    Template 1: Classic – Squat / Bench / Deadlift / (optional) WPU
    """
    captured = no_side_effects

    # Inputs sequence:
    # 1. title (blank -> default)
    # 2. template = "1"
    # 3. squat 1RM
    # 4. bench 1RM
    # 5. deadlift 1RM
    # 6. WPU bodyweight (blank -> skip)
    # 7. week (blank -> all)
    # 8. output mode "t" (text only)
    inputs = iter(
        [
            "",  # title
            "1",  # template choice -> Classic
            "455",  # squat
            "315",  # bench
            "500",  # deadlift
            "",  # WPU bodyweight skip
            "",  # week -> "all"
            "t",  # output mode
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr(cli, "input", fake_input)

    cli.run_interactive()

    args = captured["args"]
    lifts_list = args.lifts

    # Convert list to dict for easier assertions
    lifts = {lift["exercise"]: lift for lift in lifts_list}

    assert lifts["squat"]["one_rm"] == 455
    assert lifts["bench press"]["one_rm"] == 315
    assert lifts["deadlift"]["one_rm"] == 500
    # No WPU because we skipped BW
    assert "weighted pullup" not in lifts


def test_interactive_template_front_squat_block_builds_expected_lifts(
    monkeypatch, no_side_effects
):
    """
    Template 2: Front-squat Block – Front Squat / Overhead Press / Deadlift / (optional) WPU
    """
    captured = no_side_effects

    inputs = iter(
        [
            "FS Block",  # title
            "2",  # template choice -> Front-squat Block
            "355",  # front squat
            "185",  # overhead press
            "495",  # deadlift
            "200",  # WPU bodyweight
            "35x4",  # WPU set
            "3",  # week = 3
            "t",  # output mode
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr(cli, "input", fake_input)

    cli.run_interactive()

    args = captured["args"]
    lifts_list = args.lifts

    # Convert list to dict for easier assertions
    lifts = {lift["exercise"]: lift for lift in lifts_list}

    assert "squat" not in lifts
    assert "bench press" not in lifts
    assert lifts["front squat"]["one_rm"] == 355
    assert lifts["overhead press"]["one_rm"] == 185
    assert lifts["deadlift"]["one_rm"] == 495
    # WPU should be present with estimated 1RM and given BW
    assert "weighted pullup" in lifts
    assert lifts["weighted pullup"]["body_weight"] == 200


# -------------------------------------------------------------------
# Fixtures + tests for interactive templates (run_interactive)
# -------------------------------------------------------------------


@pytest.fixture
def no_side_effects(monkeypatch):
    """
    Disable clipboard + PDF side effects, and capture args passed into
    build_program_markdown for inspection.
    """
    captured = {}

    def fake_copy_to_clipboard(_text: str) -> None:
        return

    def fake_markdown_to_pdf(_md: str, _path: str, title: str | None = None) -> None:
        return

    def fake_build_program_markdown(
        args: argparse.Namespace, for_pdf: bool = False
    ) -> str:
        captured["args"] = args
        return "# TEST PROGRAM"

    monkeypatch.setattr(cli, "copy_to_clipboard", fake_copy_to_clipboard)
    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)
    monkeypatch.setattr(cli, "build_program_markdown", fake_build_program_markdown)

    return captured


def test_interactive_template_classic_builds_expected_lifts(
    monkeypatch, no_side_effects
):
    """
    Template 1: Classic – Squat / Bench / Deadlift / (optional) WPU
    """
    captured = no_side_effects

    # Inputs sequence:
    # 1. title (blank -> default)
    # 2. template = "1"
    # 3. squat 1RM
    # 4. squat bar weight (blank -> 45)
    # 5. squat bar label (blank -> no label)
    # 6. bench 1RM
    # 7. bench bar weight (blank -> 45)
    # 8. bench bar label (blank -> no label)
    # 9. deadlift 1RM
    # 10. deadlift bar weight (blank -> 45)
    # 11. deadlift bar label (blank -> no label)
    # 12. WPU bodyweight (blank -> skip)
    # 13. week (blank -> all)
    # 14. output mode "t" (text only)
    inputs = iter(
        [
            "",  # title
            "1",  # template choice -> Classic
            "455",  # squat
            "",  # squat bar weight -> default 45
            "",  # squat bar label -> no label
            "315",  # bench
            "",  # bench bar weight -> default 45
            "",  # bench bar label -> no label
            "500",  # deadlift
            "",  # deadlift bar weight -> default 45
            "",  # deadlift bar label -> no label
            "",  # WPU bodyweight skip
            "",  # week -> "all"
            "t",  # output mode
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    # ✅ patch builtins.input, not cli.input
    monkeypatch.setattr(builtins, "input", fake_input)

    cli.run_interactive()

    args = captured["args"]
    lifts_list = args.lifts

    # Convert list to dict for easier assertions
    lifts = {lift["exercise"]: lift for lift in lifts_list}

    assert lifts["squat"]["one_rm"] == 455
    assert lifts["bench press"]["one_rm"] == 315
    assert lifts["deadlift"]["one_rm"] == 500
    # No WPU because we skipped BW
    assert "weighted pullup" not in lifts


def test_interactive_template_front_squat_block_builds_expected_lifts(
    monkeypatch, no_side_effects
):
    """
    Template 2: Front-squat Block – Front Squat / Overhead Press / Deadlift / (optional) WPU
    """
    captured = no_side_effects

    inputs = iter(
        [
            "FS Block",  # title
            "2",  # template choice -> Front-squat Block
            "355",  # front squat
            "",  # front squat bar weight -> default 45
            "",  # front squat bar label -> no label
            "185",  # overhead press
            "",  # overhead press bar weight -> default 45
            "",  # overhead press bar label -> no label
            "495",  # deadlift
            "",  # deadlift bar weight -> default 45
            "",  # deadlift bar label -> no label
            "200",  # WPU bodyweight
            "35x4",  # WPU set
            "3",  # week = 3
            "t",  # output mode
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    # ✅ patch builtins.input here too
    monkeypatch.setattr(builtins, "input", fake_input)

    cli.run_interactive()

    args = captured["args"]
    lifts_list = args.lifts

    # Convert list to dict for easier assertions
    lifts = {lift["exercise"]: lift for lift in lifts_list}

    assert "squat" not in lifts
    assert "bench press" not in lifts
    assert lifts["front squat"]["one_rm"] == 355
    assert lifts["overhead press"]["one_rm"] == 185
    assert lifts["deadlift"]["one_rm"] == 495
    # WPU should be present with estimated 1RM and given BW
    assert "weighted pullup" in lifts
    assert lifts["weighted pullup"]["body_weight"] == 200


def test_interactive_template_custom_with_extra_exercises(
    monkeypatch, no_side_effects
):
    """
    Template 3: Custom with extra exercises added
    """
    captured = no_side_effects

    inputs = iter(
        [
            "Custom Program",  # title
            "3",  # template choice -> Custom
            # Lower-body main lift slot
            "1",  # choose squat
            "455",  # squat 1RM
            "",  # squat bar weight -> default 45
            "",  # squat bar label -> no label
            # Upper-body main press slot
            "1",  # choose bench press
            "315",  # bench 1RM
            "",  # bench bar weight -> default 45
            "",  # bench bar label -> no label
            # Hinge slot
            "1",  # choose deadlift
            "500",  # deadlift 1RM
            "",  # deadlift bar weight -> default 45
            "",  # deadlift bar label -> no label
            "",  # WPU bodyweight skip
            # Extra exercises
            "y",  # add extra exercises? yes
            "5",  # select overhead press (5th in EXERCISE_PROFILES keys alphabetically)
            "185",  # overhead press 1RM
            "",  # overhead press bar weight -> default 45
            "",  # overhead press bar label -> no label
            "y",  # add another? yes
            "2",  # select front squat (2nd in EXERCISE_PROFILES keys alphabetically)
            "355",  # front squat 1RM
            "",  # front squat bar weight -> default 45
            "",  # front squat bar label -> no label
            "n",  # add another? no
            "",  # week -> "all"
            "t",  # output mode
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr(builtins, "input", fake_input)

    cli.run_interactive()

    args = captured["args"]
    lifts_list = args.lifts

    # Convert list to dict for easier assertions
    lifts = {lift["exercise"]: lift for lift in lifts_list}

    # Standard slot selections
    assert lifts["squat"]["one_rm"] == 455
    assert lifts["bench press"]["one_rm"] == 315
    assert lifts["deadlift"]["one_rm"] == 500
    # Extra exercises added
    assert "overhead press" in lifts
    assert lifts["overhead press"]["one_rm"] == 185
    assert "front squat" in lifts
    assert lifts["front squat"]["one_rm"] == 355
    # No WPU because we skipped BW
    assert "weighted pullup" not in lifts
