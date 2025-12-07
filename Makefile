# ================================
# TBWeightCalc Makefile
# ================================

PACKAGE = tbweightcalc
DIST_DIR = dist
VENV_DIR = .venv
PYTHON   = $(VENV_DIR)/bin/python

# Internal helper: ensure venv exists
$(PYTHON):
	python3 -m venv $(VENV_DIR)
	$(PYTHON) -m pip install --upgrade pip setuptools wheel

# -------------------------
# Create / update venv + dev deps
# -------------------------
.PHONY: venv
venv: $(PYTHON)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .
	$(PYTHON) -m pip install pytest

# -------------------------
# Editable install via pipx (for global tbcalc)
# -------------------------
.PHONY: dev
dev:
	pipx uninstall $(PACKAGE) || true
	pipx install -e .

# -------------------------
# Run tests with pytest (in .venv)
# -------------------------
.PHONY: test
test: venv
	$(PYTHON) -m pytest -vv

# Shortcut alias
.PHONY: pytest
pytest: test

# -------------------------
# Build wheel + sdist
# -------------------------
.PHONY: build
build: venv
	$(PYTHON) -m build

# -------------------------
# Install built wheel via pipx
# -------------------------
.PHONY: install
install: build
	pipx uninstall $(PACKAGE) || true
	pipx install $(DIST_DIR)/*.whl

# -------------------------
# Uninstall from pipx
# -------------------------
.PHONY: uninstall
uninstall:
	pipx uninstall $(PACKAGE) || true

# -------------------------
# Clean build artifacts
# -------------------------
.PHONY: clean
clean:
	rm -rf $(DIST_DIR) build *.egg-info

# -------------------------
# Full rebuild + pipx install (packaged mode)
# -------------------------
.PHONY: reinstall
reinstall: clean install

# -------------------------
# Reinstall editable via pipx
# -------------------------
.PHONY: redevedit
redevedit:
	pipx uninstall $(PACKAGE) || true
	pipx install -e .

.PHONY: run
run: 
	python -m tbweightcalc.cli

# -------------------------
# Help
# -------------------------
.PHONY: help
help:
	@echo "Makefile commands:"
	@echo "  make venv       - Create .venv and install dev deps (editable + pytest)"
	@echo "  make dev        - Install package in editable mode via pipx (global tbcalc)"
	@echo "  make test       - Run pytest in .venv"
	@echo "  make pytest     - Alias for make test"
	@echo "  make build      - Build wheel + sdist (dist/)"
	@echo "  make install    - Install built wheel via pipx"
	@echo "  make uninstall  - Uninstall tbweightcalc from pipx"
	@echo "  make clean      - Remove build artifacts"
	@echo "  make reinstall  - Clean, build, and install wheel via pipx"
	@echo "  make redevedit  - Reinstall editable version via pipx"
	@echo "  make run        - Runs python -m tbweightcalc.cli directly"
