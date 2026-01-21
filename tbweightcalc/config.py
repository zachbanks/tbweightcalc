"""Configuration management for Tactical Barbell Weight Calculator."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class FormattingConfig:
    """Configuration for formatting output."""

    weight_unit: str = "lbs"  # "pounds_sign" (#), "lbs", or "pounds"
    show_weight_decimals: bool = False
    bar_indicator: str = "bar"

    def format_weight(self, weight: float) -> str:
        """Format a weight value according to config settings."""
        # Format number
        if self.show_weight_decimals or weight != int(weight):
            weight_str = f"{weight:.1f}" if weight == int(weight) else str(weight)
        else:
            weight_str = str(int(weight))

        # Apply unit
        if self.weight_unit == "pounds_sign":
            return f"{weight_str}#"
        elif self.weight_unit == "lbs":
            return f"{weight_str} lbs"
        elif self.weight_unit == "pounds":
            return f"{weight_str} pounds"
        else:
            # Fallback to lbs
            return f"{weight_str} lbs"


@dataclass
class DefaultsConfig:
    """Default values for various parameters."""

    standard_bar_weight: float = 45.0
    body_weight: Optional[float] = None


@dataclass
class OutputConfig:
    """Configuration for output generation."""

    pdf_output_dir: str = "~/Downloads"
    default_title: str = "Tactical Barbell Max Strength: {date}"
    date_format: str = "%Y-%m-%d"
    copy_to_clipboard: bool = True


@dataclass
class Config:
    """Main configuration object for tbcalc."""

    formatting: FormattingConfig = field(default_factory=FormattingConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    week_percentages: Dict[int, int] = field(
        default_factory=lambda: {1: 70, 2: 80, 3: 90, 4: 75, 5: 85, 6: 95}
    )
    available_plates: List[float] = field(
        default_factory=lambda: [45, 35, 25, 15, 10, 5, 2.5]
    )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Config:
        """Create a Config from a dictionary (typically loaded from YAML)."""
        formatting_data = data.get("formatting", {})
        defaults_data = data.get("defaults", {})
        output_data = data.get("output", {})

        return cls(
            formatting=FormattingConfig(
                weight_unit=formatting_data.get("weight_unit", "lbs"),
                show_weight_decimals=formatting_data.get("show_weight_decimals", False),
                bar_indicator=formatting_data.get("bar_indicator", "bar"),
            ),
            defaults=DefaultsConfig(
                standard_bar_weight=defaults_data.get("standard_bar_weight", 45.0),
                body_weight=defaults_data.get("body_weight"),
            ),
            output=OutputConfig(
                pdf_output_dir=output_data.get("pdf_output_dir", "~/Downloads"),
                default_title=output_data.get(
                    "default_title", "Tactical Barbell Max Strength: {date}"
                ),
                date_format=output_data.get("date_format", "%Y-%m-%d"),
                copy_to_clipboard=output_data.get("copy_to_clipboard", True),
            ),
            week_percentages=data.get(
                "week_percentages", {1: 70, 2: 80, 3: 90, 4: 75, 5: 85, 6: 95}
            ),
            available_plates=data.get("available_plates", [45, 35, 25, 15, 10, 5, 2.5]),
        )


def get_config_paths() -> List[Path]:
    """
    Return a list of config file paths to check, in priority order.

    Priority:
    1. ~/.config/tbcalc/config.yaml (user config)
    2. default_config.yaml (bundled with package)
    """
    paths = []

    # User config directory
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        user_config = Path(config_home) / "tbcalc" / "config.yaml"
    else:
        user_config = Path.home() / ".config" / "tbcalc" / "config.yaml"

    paths.append(user_config)

    # Default bundled config
    default_config = Path(__file__).parent / "default_config.yaml"
    paths.append(default_config)

    return paths


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from YAML file.

    Args:
        config_path: Optional explicit path to config file.
                    If not provided, searches standard locations.

    Returns:
        Config object with settings from file or defaults.
    """
    if yaml is None:
        # YAML not available, return default config
        return Config()

    if config_path:
        paths_to_try = [config_path]
    else:
        paths_to_try = get_config_paths()

    for path in paths_to_try:
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = yaml.safe_load(f)
                    if data:
                        return Config.from_dict(data)
            except Exception as e:
                # If config loading fails, fall back to defaults
                print(f"Warning: Failed to load config from {path}: {e}")
                continue

    # No config file found or all failed, return defaults
    return Config()


def create_user_config() -> Path:
    """
    Create a user config file from the default template.

    Returns:
        Path to the created config file.
    """
    # Determine user config location
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        config_dir = Path(config_home) / "tbcalc"
    else:
        config_dir = Path.home() / ".config" / "tbcalc"

    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.yaml"

    # Copy default config if it doesn't exist
    if not config_file.exists():
        default_config = Path(__file__).parent / "default_config.yaml"
        if default_config.exists():
            import shutil

            shutil.copy(default_config, config_file)
        else:
            # Create minimal config if default doesn't exist
            config_file.write_text(
                """# Tactical Barbell Weight Calculator Configuration

formatting:
  weight_unit: "lbs"  # Options: "pounds_sign" (#), "lbs", "pounds"
  show_weight_decimals: false
  bar_indicator: "bar"

defaults:
  standard_bar_weight: 45.0

week_percentages:
  1: 70
  2: 80
  3: 90
  4: 75
  5: 85
  6: 95

available_plates: [45, 35, 25, 15, 10, 5, 2.5]
"""
            )

    return config_file
