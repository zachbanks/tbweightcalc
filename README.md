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

Sample output

```
# Tactical Barbell Max Strength: 2025-12-09

## WEEK 1 - 70%

### SQUAT

1RM: 455#

- 2 x 5 - 45 lbs - Bar
- 1 x 5 - 135 lbs - 45
- 1 x 3 - 190 lbs - 45 25 2.5
- 1 x 2 - 255 lbs - (45 x 2) 15
- **(3-5) x 5 - 320 lbs - (45 x 3) 2.5**


### BENCH PRESS

1RM: 250#

- 2 x 5 - 45 lbs - Bar
- 1 x 5 - 95 lbs - 25
- 1 x 3 - 120 lbs - 35 2.5
- 1 x 2 - 165 lbs - 45 15
- **(3-5) x 5 - 175 lbs - 45 15 5**


### DEADLIFT

1RM: 300#

- 2 x 5 - 85 lbs - 15 5
- 1 x 3 - 125 lbs - 35 5
- 1 x 2 - 185 lbs - 45 25
- **(1-3) x 5 - 210 lbs - 45 35 2.5**


### WEIGHTED PULLUP

1RM: 67# @ BW of 200#

- **(3-5) x 5 - Bodyweight**
```
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
- **pipx**
- **Pandoc**
- **XeLaTeX**
- LaTeX packages `fancyhdr` + `titling`
- **JetBrainsMono Nerd Font Mono**

Below are the macOS install steps.

---

## 1️⃣ Manual Developer Installation (macOS)

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
```

## Install script
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/zachbanks/tbweightcalc/main/install_tbcalc.sh)"
```


## Upgrade
To upgrade to the latest version, run 
```bash
pipx upgrade tbweightcalc
```
