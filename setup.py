"""
Setup script for Cloud Drive Tools.
"""

from setuptools import find_packages, setup

setup(
    name='cloud-drive-tools',
    author='Adam Dangoor',
    author_email='adamdangoor@gmail.com',
    install_requires=['click', 'PyYAML'],
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    entry_points="""
        [console_scripts]
        cloud-drive-tools=cloud_drive_tools:cloud_drive_tools
    """,
)
