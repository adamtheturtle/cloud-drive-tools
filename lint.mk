# Make commands for linting

SHELL := /bin/bash -euxo pipefail

.PHONY: black
black:
	black --check .

.PHONY: fix-black
fix-black:
	black .

.PHONY: mypy
mypy:
	mypy .

.PHONY: check-manifest
check-manifest:
	check-manifest .

.PHONY: doc8
doc8:
	doc8 .

.PHONY: flake8
flake8:
	flake8 .

.PHONY: isort
isort:
	isort --check-only .

.PHONY: fix-isort
fix-isort:
	isort .

.PHONY: pip-extra-reqs
pip-extra-reqs:
	pip-extra-reqs --requirements-file=requirements/requirements.txt src/

.PHONY: pip-missing-reqs
pip-missing-reqs:
	pip-missing-reqs --requirements-file=requirements/requirements.txt src/

.PHONY: pylint
pylint:
	pylint *.py src/

.PHONY: pyroma
pyroma:
	pyroma --min 10 .

.PHONY: vulture
vulture:
	vulture --min-confidence 100 --exclude _vendor --exclude .eggs .

.PHONY: linkcheck
linkcheck:
	$(MAKE) -C docs/ linkcheck SPHINXOPTS=$(SPHINXOPTS)

.PHONY: spelling
spelling:
	$(MAKE) -C docs/ spelling SPHINXOPTS=$(SPHINXOPTS)

.PHONY: shellcheck
shellcheck:
	shellcheck --exclude SC2164,SC1091 */*.sh

.PHONY: autoflake
autoflake:
	autoflake \
	    --in-place \
	    --recursive \
	    --remove-all-unused-imports \
	    --remove-unused-variables \
	    --expand-star-imports \
	    --exclude _vendor,release \
	    .

.PHONY: pydocstyle
pydocstyle:
	pydocstyle

.PHONY: add-trailing-comma
add-trailing-comma:
	add-trailing-comma $$(find . -type f -name '*.py') --exit-zero-even-if-changed
