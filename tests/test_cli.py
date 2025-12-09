import argparse
from pathlib import Path
import sys
import builtins

import tbweightcalc.cli as cli


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
    assert "## WEEK 2 - 80%" in md
    # Squat line should be present somewhere
    assert "squat" in md.lower()
    # Should contain the separator '---' style HR since for_pdf=False and multiple weeks not used
    # (for a single week it shouldn't add extra HRs at end)
    assert "\\pagebreak" not in md  # that's PDF-only


def test_build_program_markdown_pdf_uses_pagebreaks():
    # This uses "all" weeks so there will be separators
    args = make_args(week="all")
    md = cli.build_program_markdown(args, for_pdf=True)

    # In PDF mode we expect raw \pagebreak between weeks
    assert "\\pagebreak" in md
    # No visible horizontal rules
    assert "---" not in md


# -------------------------------------------------------------------
# Tests for main() CLI behavior
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
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)

    # Capture the args passed into markdown_to_pdf instead of actually running it
    called = {}

    def fake_markdown_to_pdf(markdown: str, output_path: str, title: str | None = None):
        called["markdown"] = markdown
        called["output_path"] = output_path
        called["title"] = title

        # Simulate creating a file so tests can assert existence if desired
        Path(output_path).write_bytes(b"%PDF-FAKE%")

    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)

    # Patch sys.argv for argparse
    monkeypatch.setattr(cli, "argparse", cli.argparse)
    monkeypatch.setenv("PYTHONUNBUFFERED", "1")

    # Run main with patched sys.argv
    monkeypatch.setattr(cli, "os", cli.os)
    monkeypatch.setattr(cli, "Path", cli.Path)

    # Easiest: monkeypatch sys.argv in the module
    import sys

    monkeypatch.setattr(sys, "argv", argv)

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

    called = {}

    def fake_markdown_to_pdf(markdown: str, output_path: str, title: str | None = None):
        called["markdown"] = markdown
        called["output_path"] = output_path
        called["title"] = title
        Path(output_path).write_bytes(b"%PDF-FAKE%")

    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)

    import sys

    monkeypatch.setattr(sys, "argv", argv)

    cli.main()

    captured = capsys.readouterr()
    stdout = captured.out

    # Should print a heading that starts with "# Tactical Barbell Max Strength:"
    assert "# Tactical Barbell Max Strength:" in stdout

    assert called["title"] is not None
    assert called["title"].startswith("Tactical Barbell Max Strength:")
    assert Path(called["output_path"]) == pdf_path
    assert pdf_path.exists()


def test_main_interactive_text_only(monkeypatch, capsys):
    """
    When tbcalc is run with no CLI options, it should enter interactive mode.

    In this scenario the user:
      - provides a title
      - provides squat & bench 1RMs
      - skips deadlift & WPU
      - chooses text-only output
    """

    # Simulate: tbcalc  (no args)
    monkeypatch.setattr(sys, "argv", ["tbcalc"])

    # Fake user inputs for input() prompts
    inputs = iter(
        [
            "My Interactive Title",  # title
            "455",  # squat 1RM
            "250",  # bench 1RM
            "",  # deadlift (blank -> skip)
            "",  # weighted pull-up (blank -> skip)
            "all",  # week selection
            "t",  # output: text only
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    import builtins

    monkeypatch.setattr(builtins, "input", fake_input)

    # Avoid touching system clipboard in tests
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)

    # Track whether markdown_to_pdf gets called (it should NOT for text-only)
    called = {"pdf": False}

    def fake_markdown_to_pdf(markdown: str, output_path: str, title: str | None = None):
        called["pdf"] = True

    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)

    # Run main()
    cli.main()

    out = capsys.readouterr().out

    # Should print the title and some program content
    assert "My Interactive Title" in out
    assert "WEEK" in out.upper()
    assert "455" in out  # squat
    assert "250" in out  # bench
    # Deadlift and WPU were skipped, so no obvious WPU numbers
    # (you can tighten this if you want more specific checks)

    # In text-only mode, we should NOT generate a PDF
    assert called["pdf"] is False


def test_main_interactive_both_generates_pdf(monkeypatch, capsys, tmp_path):
    """
    Interactive mode with 'both' output should still call markdown_to_pdf.
    """

    monkeypatch.setattr(sys, "argv", ["tbcalc"])

    inputs = iter(
        [
            "",  # title (blank -> default title)
            "455",  # squat
            "250",  # bench
            "300",  # deadlift
            "",  # WPU (skip)
            "1",  # week = 1 only
            "b",  # output: both (text + pdf)
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    import builtins

    monkeypatch.setattr(builtins, "input", fake_input)
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)

    # Capture markdown_to_pdf arguments
    pdf_call = {}

    def fake_markdown_to_pdf(markdown: str, output_path: str, title: str | None = None):
        pdf_call["markdown"] = markdown
        pdf_call["output_path"] = output_path
        pdf_call["title"] = title
        # Simulate file creation
        Path(output_path).write_bytes(b"%PDF-FAKE%")

    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)

    cli.main()

    out = capsys.readouterr().out

    # Should print some text for week 1 with the right lifts
    assert "Week 1" in out or "WEEK 1" in out.upper()
    assert "455" in out
    assert "250" in out
    assert "300" in out

    # PDF generation should have been invoked
    assert "output_path" in pdf_call
    assert "markdown" in pdf_call
    assert pdf_call["markdown"]  # non-empty markdown
    assert pdf_call["title"] is not None


def test_main_interactive_ctrl_c_exits_cleanly(monkeypatch, capsys):
    """
    If the user hits Ctrl-C in interactive mode, main() should
    exit cleanly without propagating KeyboardInterrupt.
    """

    # Simulate: tbcalc  (no args)
    monkeypatch.setattr(sys, "argv", ["tbcalc"])

    # First call to input() raises KeyboardInterrupt, like pressing Ctrl-C
    def fake_input(prompt: str = "") -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", fake_input)

    # Make sure we don't touch clipboard or PDF in this path
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)
    monkeypatch.setattr(cli, "markdown_to_pdf", lambda *a, **k: None)

    # This should NOT raise KeyboardInterrupt; it should just print a message
    cli.main()

    out = capsys.readouterr().out
    assert "Aborted by user" in out  # or whatever message you chose


def test_prompt_one_rm(monkeypatch, capsys):
    inputs = iter(["275", "5"])

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr(builtins, "input", fake_input)

    cli.prompt_one_rm()

    out = capsys.readouterr().out
    assert "Estimated 1RM" in out
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


import builtins

import tbweightcalc.cli as cli


class TestParseWeightedPullupString:
    def test_blank_and_whitespace_return_none(self):
        assert cli.parse_weighted_pullup_string(200, "") is None
        assert cli.parse_weighted_pullup_string(200, "   ") is None

    def test_numeric_two_part_and_x_style(self):
        bw = 200

        # '35 4'  -> +35 for 4 reps  => 235 x 4
        r1 = cli.parse_weighted_pullup_string(bw, "35 4")
        # Epley: 235 * (1 + 4/30) = 235 * 34/30 ≈ 266.33 -> 266
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
        # 200 * (1 + 4/30) = 200 * 34/30 ≈ 226.67 -> 227
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
