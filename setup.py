"""
Setup script for Cloud Drive Tools.
"""

from setuptools import setup

setup(
    name='Cloud Drive Tools',
    author='Adam Dangoor',
    author_email='adamdangoor@gmail.com',
    install_requires=['click', 'PyYAML'],
    entry_points="""
        [console_scripts]
        cloud-drive-tools=cloud_drive_tools:cloud_drive_tools
    """,
)
