PYTHON ?= python

.PHONY: lint format test compile check-secrets check-english all

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m black --check .

format:
	$(PYTHON) -m ruff check . --fix
	$(PYTHON) -m black .

test:
	$(PYTHON) -m pytest

compile:
	$(PYTHON) -m compileall projects

check-secrets:
	rg -ni "(to""ken|sec""ret|pass""word|pass""wd|api[_-]?""key|access[_-]?""key|bot_""token|chat_""id|aws_""secret|BEGIN PRIVATE ""KEY)" .

check-english:
	rg -n "\p{Cyrillic}" .
	rg -ni "(course[ -]specific|platform[ -]specific|non-public)" .

all: lint compile test
