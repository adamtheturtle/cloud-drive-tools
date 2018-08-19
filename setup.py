"""
Setup script for Cloud Drive Tools.
"""

from setuptools import find_packages, setup

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
    name='cloud-drive-tools',
    author='Adam Dangoor',
    author_email='adamdangoor@gmail.com',
    install_requires=INSTALL_REQUIRES,
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    extras_require={
        'dev': DEV_REQUIRES,
    },
    entry_points="""
        [console_scripts]
        cloud-drive-tools=cloud_drive_tools:cloud_drive_tools
    """,
)
