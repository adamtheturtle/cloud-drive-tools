SHELL := /bin/bash -euxo pipefail

include lint.mk

# Treat Sphinx warnings as errors
SPHINXOPTS := -W

# At the time of writing we do not have any .sh files and so we do not run
# shellcheck.
.PHONY: lint
lint: \
    check-manifest \
    doc8 \
    flake8 \
    isort \
    mypy \
    pip-extra-reqs \
    pip-missing-reqs \
    pyroma \
    vulture \
    pylint \
    pydocstyle \
    yapf

.PHONY: fix-lint
fix-lint: \
    autoflake \
    fix-yapf \
    fix-isort
