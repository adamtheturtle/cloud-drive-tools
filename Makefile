SHELL := /bin/bash -euxo pipefail

.PHONY: yapf
yapf:
	yapf \
	    --diff \
	    --recursive \
	    .

.PHONY: fix-yapf
fix-yapf:
	yapf \
	    --in-place \
	    --recursive \
	    .

.PHONY: mypy
mypy:
	mypy *.py src/

.PHONY: check-manifest
check-manifest:
	check-manifest .

.PHONY: flake8
flake8:
	flake8 .

.PHONY: isort
isort:
	isort --recursive --check-only

.PHONY: pip-extra-reqs
pip-extra-reqs:
	pip-extra-reqs src/

.PHONY: pip-missing-reqs
pip-missing-reqs:
	pip-missing-reqs src/

.PHONY: pydocstyle
pydocstyle:
	pydocstyle

.PHONY: pylint
pylint:
	pylint *.py src/

.PHONY: pyroma
pyroma:
	pyroma .

.PHONY: vulture
vulture:
	vulture --min-confidence 100 --exclude _vendor .

.PHONY: autoflake
autoflake:
	autoflake \
	    --in-place \
	    --recursive \
	    --remove-all-unused-imports \
	    --remove-unused-variables \
	    --expand-star-imports \
	    .

# We do not use pip-missing-reqs or pip-extra-reqs as these are currently not
# working: https://github.com/r1chardj0n3s/pip-check-reqs/issues/24
.PHONY: lint
lint: \
    check-manifest \
    flake8 \
    isort \
    mypy \
    pydocstyle \
    pylint \
    vulture \
    yapf

# Fix some linting errors.
.PHONY: fix-lint
fix-lint: autoflake fix-yapf
	isort --recursive --apply
