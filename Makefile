SHELL := /bin/bash -euxo pipefail

include lint.mk

# At the time of writing we do not have any .sh files and so we do not run
# shellcheck.
.PHONY: lint
lint: \
    black \
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

.PHONY: fix-lint
fix-lint: \
    autoflake \
    fix-black \
    fix-isort
