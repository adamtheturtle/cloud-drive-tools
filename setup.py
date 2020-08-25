"""
Setup script for Cloud Drive Tools.
"""

from setuptools import setup

with open('requirements.txt') as requirements:
    INSTALL_REQUIRES = []
    for line in requirements.readlines():
        if not line.startswith('#'):
            INSTALL_REQUIRES.append(line)

with open('dev-requirements.txt') as dev_requirements:
    DEV_REQUIRES = []
    for line in dev_requirements.readlines():
        if not line.startswith('#'):
            DEV_REQUIRES.append(line)

setup(
    install_requires=INSTALL_REQUIRES,
    extras_require={
        'dev': DEV_REQUIRES,
    },
)
