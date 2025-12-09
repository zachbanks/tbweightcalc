#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# tbcalc install script (lightweight LaTeX version)
# ============================================================
# - Detects macOS or Ubuntu/Debian Linux
# - Installs system dependencies:
#       pandoc, XeLaTeX (minimal), JetBrainsMono Nerd Font
# - Installs pipx (if missing)
# - Installs tbcalc globally so `tbcalc` works anywhere
# ============================================================

GITHUB_REPO="zachbanks/tbweightcalc"   # ← your GitHub repo
PACKAGE_NAME="tbweightcalc"            # must match [project.name] in pyproject.toml

echo "==> Detecting operating system..."
OS="$(uname -s)"
case "$OS" in
  Darwin)
    PLATFORM="macos"
    echo "   ✔ macOS detected"
    ;;
  Linux)
    PLATFORM="linux"
    echo "   ✔ Linux detected"
    ;;
  *)
    echo "❌ ERROR: Unsupported OS: $OS"
    echo "   This installer supports macOS and Debian/Ubuntu Linux."
    exit 1
    ;;
esac

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# ------------------------------------------------------------
# macOS: ensure Homebrew
# ------------------------------------------------------------
if [ "$PLATFORM" = "macos" ]; then
  if ! command_exists brew; then
    echo "==> Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo "==> Homebrew installed. You may need to restart your terminal after this script."
  else
    echo "==> ✔ Homebrew already installed."
  fi
fi

# ------------------------------------------------------------
# System dependencies
# ------------------------------------------------------------
if [ "$PLATFORM" = "macos" ]; then
  echo "==> Installing pandoc..."
  brew install pandoc || true

  echo "==> Installing BasicTeX (minimal LaTeX with XeLaTeX)..."
  brew install --cask basictex || true

  echo "==> Ensuring TeX bin directory is on PATH..."
  TEXBIN="/Library/TeX/texbin"
  if ! echo "$PATH" | grep -q "$TEXBIN"; then
    echo "export PATH=\"$TEXBIN:\$PATH\"" >> "${HOME}/.zshrc"
    export PATH="$TEXBIN:$PATH"
  fi

  echo "==> Updating tlmgr and installing required LaTeX packages..."
  sudo tlmgr update --self || true
  sudo tlmgr install fancyhdr titling || true

  echo "==> Installing JetBrainsMono Nerd Font..."
  brew tap homebrew/cask-fonts || true
  brew install --cask font-jetbrains-mono-nerd-font || true

else
  # Linux (Debian/Ubuntu assumed)
  if ! command_exists apt && ! command_exists apt-get; then
    echo "❌ ERROR: Non-apt Linux detected."
    echo "Install manually:"
    echo "  sudo apt install pandoc texlive-xetex texlive-latex-recommended texlive-latex-extra"
    echo "  (optional) install JetBrainsMono Nerd Font"
    echo "Then:"
    echo "  pipx install \"git+https://github.com/${GITHUB_REPO}.git\""
    exit 1
  fi

  echo "==> Updating apt package lists..."
  sudo apt update -y

  echo "==> Installing pandoc + minimal LaTeX with XeLaTeX..."
  sudo apt install -y pandoc texlive-xetex texlive-latex-recommended texlive-latex-extra

  echo "==> Installing JetBrainsMono Nerd Font (user-local)..."
  FONT_DIR="${HOME}/.local/share/fonts"
  mkdir -p "$FONT_DIR"
  TMP_DIR="$(mktemp -d)"
  (
    cd "$TMP_DIR"
    curl -LO https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip
    unzip -o JetBrainsMono.zip -d "$FONT_DIR"
  )
  rm -rf "$TMP_DIR"
  fc-cache -fv || true
fi

# ------------------------------------------------------------
# Install pipx if missing
# ------------------------------------------------------------
if ! command_exists pipx; then
  echo "==> pipx not found. Installing..."

  if [ "$PLATFORM" = "macos" ] && command_exists brew; then
    brew install pipx
    pipx ensurepath || true
  else
    if command_exists python3; then
      python3 -m pip install --user pipx
      python3 -m pipx ensurepath || true
    else
      echo "❌ ERROR: python3 not found. Please install Python 3.10+ first."
      exit 1
    fi
  fi
else
  echo "==> ✔ pipx already installed."
fi

echo "==> pipx version: $(pipx --version)"

# ------------------------------------------------------------
# Install or upgrade tbcalc via pipx
# ------------------------------------------------------------
echo "==> Installing tbcalc from GitHub: ${GITHUB_REPO}"
PIPX_URL="git+https://github.com/${GITHUB_REPO}.git"

if pipx list 2>/dev/null | grep -q "${PACKAGE_NAME}"; then
  echo "==> Package already installed — upgrading..."
  pipx install --force "${PIPX_URL}"
else
  pipx install "${PIPX_URL}"
fi

echo ""
echo "============================================================"
echo "🎉 Installation complete!"
echo ""
echo "Run tbcalc with:"
echo "    tbcalc -h"
echo ""
echo "If 'tbcalc' is not found, restart your terminal or run:"
echo "    python3 -m pipx ensurepath"
echo "============================================================"
