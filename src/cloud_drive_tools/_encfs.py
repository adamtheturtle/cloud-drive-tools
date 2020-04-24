"""
Tools for interacting with ``encfs``.
"""

import subprocess
from pathlib import Path


def encode_with_encfs(
    encfs_pass: str,
    file_path_or_name: Path,
    root_dir: Path,
) -> str:
    """
    Return the encfs encoded file path.
    """
    encfsctl_args = [
        'encfsctl',
        'encode',
        '--extpass',
        f'echo {encfs_pass}',
        str(root_dir),
        str(file_path_or_name),
    ]

    encfsctl_result = subprocess.run(
        args=encfsctl_args,
        check=True,
        stdout=subprocess.PIPE,
    )

    encname = encfsctl_result.stdout.decode().strip()
    return encname
