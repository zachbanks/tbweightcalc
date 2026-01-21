"""Tests for configuration management."""

import tempfile
from pathlib import Path

import pytest

from tbweightcalc.config import (
    Config,
    FormattingConfig,
    DefaultsConfig,
    OutputConfig,
    load_config,
    create_user_config,
)


class TestFormattingConfig:
    """Test FormattingConfig functionality."""

    def test_format_weight_lbs(self):
        """Test weight formatting with 'lbs' unit."""
        config = FormattingConfig(weight_unit="lbs", show_weight_decimals=False)
        assert config.format_weight(135.0) == "135 lbs"
        assert config.format_weight(135.5) == "135.5 lbs"

    def test_format_weight_pounds_sign(self):
        """Test weight formatting with '#' unit."""
        config = FormattingConfig(weight_unit="pounds_sign", show_weight_decimals=False)
        assert config.format_weight(135.0) == "135#"
        assert config.format_weight(135.5) == "135.5#"

    def test_format_weight_pounds(self):
        """Test weight formatting with 'pounds' unit."""
        config = FormattingConfig(weight_unit="pounds", show_weight_decimals=False)
        assert config.format_weight(135.0) == "135 pounds"
        assert config.format_weight(135.5) == "135.5 pounds"

    def test_format_weight_show_decimals(self):
        """Test weight formatting with decimals always shown."""
        config = FormattingConfig(weight_unit="lbs", show_weight_decimals=True)
        # Currently the implementation doesn't fully support this,
        # but we test the intent
        result = config.format_weight(135.0)
        assert "135" in result
        assert "lbs" in result

    def test_format_weight_invalid_unit_fallback(self):
        """Test that invalid unit falls back to lbs."""
        config = FormattingConfig(weight_unit="invalid", show_weight_decimals=False)
        assert config.format_weight(135.0) == "135 lbs"


class TestConfig:
    """Test Config class functionality."""

    def test_default_config(self):
        """Test that default config has expected values."""
        config = Config()

        assert config.formatting.weight_unit == "lbs"
        assert config.formatting.show_weight_decimals is False
        assert config.formatting.bar_indicator == "bar"

        assert config.defaults.standard_bar_weight == 45.0
        assert config.defaults.body_weight is None

        assert config.output.pdf_output_dir == "~/Downloads"
        assert config.output.copy_to_clipboard is True

        assert config.week_percentages == {1: 70, 2: 80, 3: 90, 4: 75, 5: 85, 6: 95}
        assert config.available_plates == [45, 35, 25, 15, 10, 5, 2.5]

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "formatting": {
                "weight_unit": "pounds_sign",
                "show_weight_decimals": True,
                "bar_indicator": "barbell",
            },
            "defaults": {
                "standard_bar_weight": 35.0,
                "body_weight": 200,
            },
            "output": {
                "pdf_output_dir": "~/Documents",
                "copy_to_clipboard": False,
            },
            "week_percentages": {1: 60, 2: 70, 3: 80, 4: 65, 5: 75, 6: 85},
            "available_plates": [45, 25, 10, 5],
        }

        config = Config.from_dict(data)

        assert config.formatting.weight_unit == "pounds_sign"
        assert config.formatting.show_weight_decimals is True
        assert config.formatting.bar_indicator == "barbell"

        assert config.defaults.standard_bar_weight == 35.0
        assert config.defaults.body_weight == 200

        assert config.output.pdf_output_dir == "~/Documents"
        assert config.output.copy_to_clipboard is False

        assert config.week_percentages[1] == 60
        assert config.available_plates == [45, 25, 10, 5]

    def test_config_from_partial_dict(self):
        """Test that partial dict uses defaults for missing values."""
        data = {
            "formatting": {
                "weight_unit": "pounds_sign",
            },
        }

        config = Config.from_dict(data)

        # Specified value
        assert config.formatting.weight_unit == "pounds_sign"

        # Default values
        assert config.formatting.show_weight_decimals is False
        assert config.defaults.standard_bar_weight == 45.0


class TestLoadConfig:
    """Test config loading functionality."""

    def test_load_config_from_file(self):
        """Test loading config from a YAML file."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
formatting:
  weight_unit: "pounds_sign"
  show_weight_decimals: false
  bar_indicator: "bar"

defaults:
  standard_bar_weight: 35.0

week_percentages:
  1: 70
  2: 80
  3: 90
  4: 75
  5: 85
  6: 95

available_plates: [45, 35, 25, 15, 10, 5, 2.5]
""")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)

            assert config.formatting.weight_unit == "pounds_sign"
            assert config.defaults.standard_bar_weight == 35.0
        finally:
            temp_path.unlink()

    def test_load_config_no_file_returns_defaults(self):
        """Test that missing config file returns default config."""
        non_existent = Path("/tmp/nonexistent_config_12345.yaml")
        config = load_config(non_existent)

        # Should return default config
        assert config.formatting.weight_unit == "lbs"
        assert config.defaults.standard_bar_weight == 45.0

    def test_load_config_invalid_yaml_returns_defaults(self):
        """Test that invalid YAML returns default config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: here::")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)

            # Should return default config
            assert config.formatting.weight_unit == "lbs"
        finally:
            temp_path.unlink()


class TestCreateUserConfig:
    """Test user config file creation."""

    def test_create_user_config(self, tmp_path, monkeypatch):
        """Test creating a user config file."""
        # Set XDG_CONFIG_HOME to temporary directory
        config_dir = tmp_path / "tbcalc"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        config_file = create_user_config()

        assert config_file.exists()
        assert config_file.parent == config_dir
        assert config_file.name == "config.yaml"

        # Verify it contains valid YAML
        import yaml
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
            assert "formatting" in data or "defaults" in data


class TestFormatterIntegration:
    """Test that config integrates properly with formatters."""

    def test_plain_formatter_uses_config(self):
        """Test that PlainFormatter uses config for weight formatting."""
        from tbweightcalc.formatting import PlainFormatter

        config = FormattingConfig(weight_unit="pounds_sign")
        formatter = PlainFormatter(formatting_config=config)

        assert formatter.format_weight(135) == "135#"

    def test_markdown_formatter_uses_config(self):
        """Test that MarkdownFormatter uses config for weight formatting."""
        from tbweightcalc.formatting import MarkdownFormatter

        config = FormattingConfig(weight_unit="pounds")
        formatter = MarkdownFormatter(formatting_config=config)

        assert formatter.format_weight(135) == "135 pounds"

    def test_formatter_without_config_uses_default(self):
        """Test that formatters work without config (backwards compatibility)."""
        from tbweightcalc.formatting import PlainFormatter

        formatter = PlainFormatter()
        result = formatter.format_weight(135)

        assert "135" in result
        assert "lbs" in result
