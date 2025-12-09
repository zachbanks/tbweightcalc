# TBWeightCalc
### Tactical Barbell Max Strength Calculator + PDF Generator  
**Command:** `tbcalc`

TBWeightCalc is a command-line tool for generating *Tactical Barbell Max Strength* programming sheets from your 1RM values. It outputs:

- Clean, readable **Markdown**
- Auto-copied **clipboard output** (macOS)
- A fully formatted **PDF** with:
  - Centered title  
  - JetBrainsMono Nerd Font Mono  
  - Page numbers  
  - Date footer  
  - Automatic page breaks  
  - Clean layout optimized for printing  

It is designed for speed, clarity, and usability — perfect for Tactical Barbell strength cycles.

---

# 🚀 Features

- Computes weekly training sets for:
  - **Squat**
  - **Bench Press**
  - **Deadlift**
  - **Weighted Pull-Up** (1RM + bodyweight)
- Generates:
  - **All 6 weeks** or a **single week**
  - **Markdown output**
  - **PDF output (via XeLaTeX + Pandoc)**
- Uses JetBrainsMono Nerd Font Mono for a highly readable layout
- Automatically copies Markdown to clipboard (macOS)
- One simple CLI command: `tbcalc`

---

# 📦 Installation Guide (macOS)

TBWeightCalc requires the following system dependencies:

### **Required**
- Python **3.10+**
- **pipx** (recommended installation method)
- **Pandoc**
- **XeLaTeX** (BasicTeX installation)
- LaTeX packages:
  - `fancyhdr`
  - `titling`
- **JetBrainsMono Nerd Font Mono**

Below are full instructions for installing on a brand-new Mac.

---

## 1️⃣ Install pipx (recommended)

pipx installs CLI tools globally *without* modifying your system Python.

```bash
brew install pipx
pipx ensurepath

brew install pandoc
brew install --cask basictex
echo 'export PATH="/Library/TeX/texbin:$PATH"' >> ~/.zshrc
source ~/.zshrc

sudo tlmgr update --self
sudo tlmgr install fancyhdr titling
brew install --cask font-jetbrains-mono-nerd-font
pipx install tbweightcalc

Usage
tbcalc -dl 300 -sq 455 -bp 250 -wpu 252 210 --title "TB 2025-03"


## Installation (macOS / Ubuntu with pipx)

This script will:

- Install system dependencies (pandoc, LaTeX engine, JetBrainsMono Nerd Font)
- Install `pipx` (if needed)
- Install `tbcalc` so it’s available as a global command

Run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/zachbanks/tbweightcalc/main/install_tbcalc.sh)"
```
