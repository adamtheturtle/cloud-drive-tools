"""
Tools for managing an encrypted directory on a cloud drive.

See https://github.com/msh100/ACDTools/blob/gdrive-support/acdtools for
the inspiration.
"""

import datetime
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Dict, Optional, Union

import click
import yaml

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class _Config:
    def __init__(
        self,
        cloud_drive_tools_path: Path,
        data_dir: Path,
        days_to_keep_local: float,
        encfs6_config: Path,
        encfs_pass: str,
        mount_base: Path,
        path_on_cloud_drive: str,
        rclone: Path,
        rclone_config_path: Path,
        rclone_remote: str,
        rclone_verbose: bool,
    ):
        """
        Configuration for cloud drive tools.
        """
        self.cloud_drive_tools_path = cloud_drive_tools_path
        self.data_dir = data_dir
        self.days_to_keep_local = days_to_keep_local
        self.encfs6_config = encfs6_config
        self.encfs_pass = encfs_pass
        self.path_on_cloud_drive = path_on_cloud_drive
        self.rclone = rclone
        message = f'"{rclone}" is not available on the PATH.'
        assert shutil.which(str(rclone)) is not None, message
        self.rclone_config_path = rclone_config_path
        self.rclone_remote = rclone_remote
        self.rclone_verbose = rclone_verbose
        self._mount_base = mount_base
        self.remote_encrypted = mount_base / 'cloud-drive-encrypted'
        self.remote_decrypted = mount_base / 'cloud-drive-decrypted'
        self.local_encrypted = mount_base / 'local-encrypted'
        self.local_decrypted = mount_base / 'local-decrypted'
        unmount_lock_file_name = 'cloud-drive-tools-unmount.lock'
        self.unmount_lock_file = Path(__file__).parent / unmount_lock_file_name
        # We should probably explicitly pass this to subprocesses.
        os.environ['ENCFS6_CONFIG'] = str(encfs6_config)

    def as_dict(self) -> Dict[str, Union[str, float, bool]]:
        return {
            'cloud_drive_tools_path': str(self.cloud_drive_tools_path),
            'data_dir': str(self.data_dir),
            'days_to_keep_local': self.days_to_keep_local,
            'encfs6_config': str(self.encfs6_config),
            'encfs_pass': self.encfs_pass,
            'mount_base': str(self._mount_base),
            'path_on_cloud_drive': self.path_on_cloud_drive,
            'rclone': str(self.rclone),
            'rclone_config_path': str(self.rclone_config_path),
            'rclone_remote': self.rclone_remote,
            'rclone_verbose': self.rclone_verbose,
        }


@click.group(name='cloud-drive-tools')
def cloud_drive_tools() -> None:
    """
    Manage Plex tools.
    """
    message = (
        'Require a version of Python with a fix for '
        'https://bugs.python.org/issue35192'
    )
    if sys.version_info.major == 3 and sys.version_info.minor == 6:
        assert sys.version_info.micro >= 2, message

    dependencies = ('unionfs-fuse', 'encfs', 'fusermount')
    for dependency in dependencies:
        message = f'"{dependency}" is not available on the PATH.'
        assert shutil.which(str(dependency)) is not None, message


def _rclone_verbosity_flag(verbose: bool) -> str:
    """
    Verbosity flag to use with ``rclone``.
    """
    if verbose:
        return '-vv'
    return '-v'


def _rclone_path(
    rclone_remote: str,
    rclone_root: str,
    rclone_relative_path: Optional[str],
) -> str:
    """
    Return the ``rclone`` path to use.
    """
    if rclone_relative_path is None:
        return f'{rclone_remote}:{rclone_root}'

    return f'{rclone_remote}:{rclone_root}/{rclone_relative_path}'


def _get_config(
    ctx: click.core.Context,
    param: Union[click.core.Option, click.core.Parameter],
    value: Optional[Union[int, bool, str]],
) -> _Config:
    # We "use" variables to satisfy linting tools.
    for _ in (ctx, param):
        pass

    required_keys = set(
        [
            'cloud_drive_tools_path',
            'data_dir',
            'days_to_keep_local',
            'encfs6_config',
            'encfs_pass',
            'mount_base',
            'path_on_cloud_drive',
            'rclone',
            'rclone_config_path',
            'rclone_remote',
            'rclone_verbose',
        ],
    )
    allowed_keys = required_keys

    config_text = Path(str(value)).read_text()
    config = yaml.load(config_text, Loader=yaml.FullLoader) or {}

    missing_required_keys = required_keys - config.keys()
    extra_keys = config.keys() - allowed_keys

    if missing_required_keys:
        message = (
            'Using configuration file at "{config_file_path}". '
            'Missing the following configuration keys: {missing_keys}.'
        ).format(
            config_file_path=str(value),
            missing_keys=', '.join(missing_required_keys),
        )
        raise click.BadParameter(message)

    if extra_keys:
        message = (
            'Using configuration file at "{config_file_path}". '
            'The following keys were given but are not valid: {extra_keys}.'
        ).format(
            config_file_path=str(value),
            extra_keys=', '.join(extra_keys),
        )
        raise click.BadParameter(message)

    return _Config(
        cloud_drive_tools_path=Path(config['cloud_drive_tools_path']),
        data_dir=Path(config['data_dir']),
        days_to_keep_local=float(config['days_to_keep_local']),
        encfs6_config=Path(config['encfs6_config']),
        encfs_pass=str(config['encfs_pass']),
        mount_base=Path(config['mount_base']),
        path_on_cloud_drive=str(config['path_on_cloud_drive']),
        rclone=Path(config['rclone']),
        rclone_config_path=Path(config['rclone_config_path']),
        rclone_remote=str(config['rclone_remote']),
        rclone_verbose=bool(config['rclone_verbose']),
    )


def config_option(command: Callable[..., None]) -> Callable[..., None]:
    """
    Click option for passing a configuration file.
    """
    default_config_path = Path('vars.yaml')

    function = click.option(
        '--config',
        '-c',
        type=click.Path(exists=True),
        callback=_get_config,
        default=str(default_config_path),
        help='The path to a file including configuration YAML.',
    )(command)  # type: Callable[..., None]
    return function


def _local_cleanup(days_to_keep_local: float, local_decrypted: Path) -> None:
    """
    Delete local data older than "days_to_keep_local" from the configuration
    file.
    """
    message = (
        f'Deleting local files older than "{days_to_keep_local}" days old.'
    )

    LOGGER.info(message)

    seconds_to_keep_local = days_to_keep_local * 24 * 60 * 60

    file_paths = local_decrypted.rglob('*')

    now_timestamp = datetime.datetime.now().timestamp()
    oldest_acceptable_time = now_timestamp - seconds_to_keep_local

    for path in file_paths:
        ctime = path.stat().st_ctime
        if path.is_file() and ctime < oldest_acceptable_time:
            path.unlink()

    message = (
        f'Finished deleting local files older than "{days_to_keep_local}" '
        'days old.'
    )

    LOGGER.info(message)


def _is_mountpoint(name: str) -> bool:
    proc_mounts = Path('/proc/mounts').read_text().split('\n')
    for mount_line in proc_mounts:
        if mount_line:
            path = mount_line.split()[1]
            if path == name:
                return True
    return False


def _unmount(mountpoint: Path) -> None:
    """
    Unmount a mountpoint. Will not unmount if not already mounted.

    This does not work on macOS as ``fusermount`` does not exist.
    """
    if not _is_mountpoint(name=str(mountpoint)):
        message = f'Cannot unmount "{mountpoint}" - it is not mounted'
        LOGGER.warning(msg=message)
        return

    message = f'Unmounting "{mountpoint}"'
    LOGGER.info(msg=message)
    unmount_args = ['fusermount', '-u', str(mountpoint)]
    subprocess.run(args=unmount_args, check=True)


def _unmount_all(
    data_dir: Path,
    remote_encrypted: Path,
    unmount_lock_file: Path,
    local_encrypted: Path,
    remote_decrypted: Path,
) -> None:
    message = 'Unmounting all Cloud Drive Tools mountpoints'
    LOGGER.info(message)

    _unmount(mountpoint=data_dir)
    unmount_lock_file.touch()
    _unmount(mountpoint=remote_encrypted)
    time.sleep(6)
    try:
        unmount_lock_file.unlink()
    except FileNotFoundError:
        pass
    _unmount(mountpoint=remote_decrypted)
    _unmount(mountpoint=local_encrypted)


@click.command('unmount')
@config_option
def unmount_all(config: _Config) -> None:
    """
    Unmount all mountpoints associated with Cloud Drive Tools.
    """
    _unmount_all(
        data_dir=config.data_dir,
        remote_encrypted=config.remote_encrypted,
        unmount_lock_file=config.unmount_lock_file,
        local_encrypted=config.local_encrypted,
        remote_decrypted=config.remote_decrypted,
    )


@click.command('upload')
@config_option
@click.pass_context
def upload(ctx: click.core.Context, config: _Config) -> None:
    """
    Upload local data to the cloud.
    """
    upload_pid_file = Path(__file__).parent / 'upload.pid'
    if upload_pid_file.exists():
        running_pid = upload_pid_file.read_text()
        if running_pid:
            proc_file = Path('/proc') / running_pid
            if proc_file.exists():
                message = 'Upload script already running'
                LOGGER.error(msg=message)
                ctx.fail(message=message)

    current_pid = os.getpid()
    upload_pid_file.write_text(str(current_pid))
    _sync_deletes(
        local_decrypted=config.local_decrypted,
        encfs_pass=config.encfs_pass,
        remote_encrypted=config.remote_encrypted,
        rclone_remote=config.rclone_remote,
        path_on_cloud_drive=config.path_on_cloud_drive,
        rclone_config_path=config.rclone_config_path,
        rclone=config.rclone,
        rclone_verbose=config.rclone_verbose,
    )

    # Determine the .unionfs-fuse directory name as to not upload it
    exclude_name = _encode_with_encfs(
        path_or_file_name='.unionfs-fuse',
        encfs_pass=config.encfs_pass,
        root_dir=config.remote_encrypted,
    )

    upload_args = [
        str(config.rclone),
        '--config',
        str(config.rclone_config_path),
        _rclone_verbosity_flag(verbose=config.rclone_verbose),
        'copy',
        # Try to avoid Google 403: User Rate Limit Exceeded.
        # This happens when 10 total transfers happen in a second.
        '--tpslimit',
        '1',
        # Try to avoid limit of uploading files > 100 GB.
        '--max-size',
        '100G',
        # Avoid retrying when the 750 GB / day upload limit is hit.
        '--drive-stop-on-upload-limit',
        # Make fewer API requests.
        '--fast-list',
        # Exclude the ``.unionfs-fuse`` directory as this is where files to be
        # deleted go.
        '--exclude',
        f'/{exclude_name}/*',
        str(config.local_encrypted),
        _rclone_path(
            rclone_remote=config.rclone_remote,
            rclone_root=config.path_on_cloud_drive,
            rclone_relative_path=None,
        ),
    ]

    children = config.local_encrypted.glob('*')
    if children:
        subprocess.run(args=upload_args, check=True)
    else:
        message = f'{config.local_encrypted} is empty - nothing to upload'
        LOGGER.info(msg=message)

    message = 'Upload Complete - Syncing changes'
    LOGGER.info(message)
    _local_cleanup(
        days_to_keep_local=config.days_to_keep_local,
        local_decrypted=config.local_decrypted,
    )
    upload_pid_file.unlink()


def _sync_deletes(
    local_decrypted: Path,
    encfs_pass: str,
    remote_encrypted: Path,
    rclone_remote: str,
    path_on_cloud_drive: str,
    rclone_config_path: Path,
    rclone: Path,
    rclone_verbose: bool,
) -> None:
    search_dir = local_decrypted / '.unionfs-fuse'

    if not (search_dir.exists() and search_dir.is_dir()):
        message = 'No .unionfs-fuse/ directory found, nothing to delete'
        LOGGER.info(message)
        return

    hidden_flag = '_HIDDEN~'
    matched_files = search_dir.rglob(pattern='*' + hidden_flag)

    failed_sync_deletes = False

    for matched_file in matched_files:
        hidden_relative_file_path = matched_file.relative_to(search_dir)
        assert str(hidden_relative_file_path).endswith(hidden_flag)
        not_hidden_relative_file = Path(
            str(hidden_relative_file_path)[:-len(hidden_flag)],
        )
        encname = _encode_with_encfs(
            path_or_file_name=str(not_hidden_relative_file),
            encfs_pass=encfs_pass,
            root_dir=remote_encrypted,
        )

        if not encname:
            message = 'Empty name returned from encfsctl - skipping.'
            LOGGER.error(message)
            failed_sync_deletes = True
            continue

        rclone_path = _rclone_path(
            rclone_remote=rclone_remote,
            rclone_root=path_on_cloud_drive,
            rclone_relative_path=encname,
        )

        message = f'Attempting to delete "{rclone_path}"'
        LOGGER.info(message)

        rclone_args = [
            str(rclone),
            '--config',
            str(rclone_config_path),
            _rclone_verbosity_flag(verbose=rclone_verbose),
            'ls',
            '--max-depth',
            '1',
            rclone_path,
        ]

        rclone_output = subprocess.run(args=rclone_args, check=False)
        rclone_status_code = rclone_output.returncode
        if rclone_status_code:
            # This may be shown for each file in a directory if a directory is
            # deleted.
            message = f'{not_hidden_relative_file} is not on a cloud drive'
            LOGGER.info(message)
        else:
            message = (
                f'{not_hidden_relative_file} exists on cloud drive - deleting'
            )
            LOGGER.info(message)

            if matched_file.is_file():
                delete_cmd = 'delete'
            else:
                # We use purge rather than delete because ``rclone delete``
                # does not delete directories, only their contents.
                delete_cmd = 'purge'

            rclone_delete_args = [
                str(rclone),
                '--config',
                str(rclone_config_path),
                _rclone_verbosity_flag(verbose=rclone_verbose),
                delete_cmd,
                rclone_path,
            ]

            subprocess.run(args=rclone_delete_args, check=True)
            message = f'{matched_file} deleted from cloud drive'
            LOGGER.info(message)

        # Remove the UnionFS hidden object.
        if matched_file.is_file():
            matched_file.unlink()
        else:
            shutil.rmtree(matched_file)

    if not failed_sync_deletes:
        # Delete the search directory so that it is not uploaded as an
        # empty directory.
        shutil.rmtree(search_dir)
        return

    message = 'Not clearing .unionfs directory as there were failures.'
    LOGGER.warning(message)


@click.command('sync-deletes')
@config_option
def sync_deletes(config: _Config) -> None:
    """
    Reflect unionfs deleted file objects on Google Drive.
    """
    _sync_deletes(
        local_decrypted=config.local_decrypted,
        encfs_pass=config.encfs_pass,
        remote_encrypted=config.remote_encrypted,
        rclone_remote=config.rclone_remote,
        path_on_cloud_drive=config.path_on_cloud_drive,
        rclone_config_path=config.rclone_config_path,
        rclone=config.rclone,
        rclone_verbose=config.rclone_verbose,
    )


def _create_dirs(
    remote_encrypted: Path,
    remote_decrypted: Path,
    local_encrypted: Path,
    local_decrypted: Path,
    data_dir: Path,
) -> None:
    """
    Create necessary directories if they do not exist.
    """
    dirs_to_create = [
        remote_encrypted,
        remote_decrypted,
        local_encrypted,
        local_decrypted,
        data_dir,
    ]

    for directory in dirs_to_create:
        # On older Python versions, this may raise a ``FileExistsError``
        # erroneously.
        # See https://bugs.python.org/issue35192.
        #
        # However, it is also possible that two tools will be trying to make
        # this in parallel.
        # This is not concurrency-safe, so we ignore the error:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            message = (
                f'Directory "{directory}" already exists and an error was '
                'raised which we are ignoring.'
            )
            LOGGER.info(message)


def _wait_for_remote_mount(
    ctx: click.core.Context,
    remote_encrypted: Path,
    path_on_cloud_drive: str,
) -> None:
    """
    Wait for the rclone mount or error if it does not start within some time
    close to 25 seconds.
    """
    remote_mount = remote_encrypted / Path(path_on_cloud_drive).relative_to('/')
    attempts = 0
    max_attempts = 5
    sleep_seconds = 5

    while not os.path.exists(remote_mount):
        attempts += 1
        if attempts > max_attempts:
            message = 'Remote mount not found after 5 attempts, exiting'
            ctx.fail(message)

        message = f'Remote mount {remote_mount} does not exist yet, waiting.'
        LOGGER.info(message)
        time.sleep(sleep_seconds)


def _mount_data_dir(
    remote_encrypted: Path,
    remote_decrypted: Path,
    local_encrypted: Path,
    local_decrypted: Path,
    data_dir: Path,
    encfs_pass: str,
    path_on_cloud_drive: str,
) -> None:
    """
    Mount the local data directory.

    This expects that the cloud drive is mounted.
    """

    message = 'Mounting local encrypted filesystem'
    LOGGER.info(message)
    encfs_args = [
        'encfs',
        '--extpass',
        f'echo {encfs_pass}',
        '--reverse',
        str(local_decrypted),
        str(local_encrypted),
    ]
    subprocess.run(args=encfs_args, check=True)

    # pathlib.Path does not handle `///` well in a path.
    remote_mount = f'{remote_encrypted}//{path_on_cloud_drive}'
    message = 'Mounting cloud decrypted filesystem'
    LOGGER.info(message)
    encfs_args = [
        'encfs',
        '--extpass',
        f'echo {encfs_pass}',
        remote_mount,
        str(remote_decrypted),
    ]
    subprocess.run(args=encfs_args, check=True)

    message = 'Mounting UnionFS'
    LOGGER.info(message)
    unionfs_fuse_args = [
        'unionfs-fuse',
        '-o',
        'cow,allow_other',
        f'{local_decrypted}=RW:{remote_decrypted}=RO',
        str(data_dir),
    ]
    subprocess.run(args=unionfs_fuse_args, check=True)


@click.command('mount-data-dir')
@config_option
@click.pass_context
def mount_data_dir(ctx: click.core.Context, config: _Config) -> None:
    """
    Mount the data directory.
    """
    _wait_for_remote_mount(
        ctx=ctx,
        remote_encrypted=config.remote_encrypted,
        path_on_cloud_drive=config.path_on_cloud_drive,
    )

    _mount_data_dir(
        remote_encrypted=config.remote_encrypted,
        remote_decrypted=config.remote_decrypted,
        local_encrypted=config.local_encrypted,
        local_decrypted=config.local_decrypted,
        data_dir=config.data_dir,
        encfs_pass=config.encfs_pass,
        path_on_cloud_drive=config.path_on_cloud_drive,
    )


def _mount_cloud_storage(
    rclone_remote: str,
    unmount_lock_file: Path,
    rclone: Path,
    rclone_verbose: bool,
    remote_encrypted: Path,
) -> None:
    """
    Mount the cloud storage in the foreground.
    Unless an unmount operation is started, this can run forever, logging
    what is happening with the cloud storage.
    """
    rclone_path = _rclone_path(
        rclone_remote=rclone_remote,
        rclone_root='/',
        rclone_relative_path=None,
    )

    while not unmount_lock_file.exists():
        message = 'Running cloud storage mount in the foreground'
        LOGGER.info(message)
        _unmount(mountpoint=remote_encrypted)
        mount_args = [
            str(rclone),
            'mount',
            rclone_path,
            str(remote_encrypted),
            '--allow-other',
            '--read-only',
            '--umask',
            '000',
            _rclone_verbosity_flag(verbose=rclone_verbose),
            '--fast-list',
            '--dir-cache-time',
            '24h',
        ]

        subprocess.run(args=mount_args, check=True)

        message = (
            'Cloud storage mount exited - checking if to remount in a couple '
            'of seconds'
        )
        LOGGER.info(message)
        time.sleep(2)

    message = 'The cloud drive mount exited cleanly'
    LOGGER.info(message)
    unmount_lock_file.unlink()


def _encode_with_encfs(
    encfs_pass: str,
    path_or_file_name: str,
    root_dir: Path,
) -> str:
    """
    Return an encfs encoded path.
    """
    encfsctl_args = [
        'encfsctl',
        'encode',
        '--extpass',
        f'echo {encfs_pass}',
        str(root_dir),
        path_or_file_name,
    ]

    encfsctl_result = subprocess.run(
        args=encfsctl_args,
        check=True,
        stdout=subprocess.PIPE,
    )

    encname = encfsctl_result.stdout.decode().strip()
    return encname


def _decode_with_encfs(
    encfs_pass: str,
    path_or_file_name: str,
    root_dir: Path,
) -> str:
    """
    Return an encfs decoded path.
    """
    encfsctl_args = [
        'encfsctl',
        'decode',
        '--extpass',
        f'echo {encfs_pass}',
        str(root_dir),
        path_or_file_name,
    ]

    encfsctl_result = subprocess.run(
        args=encfsctl_args,
        check=True,
        stdout=subprocess.PIPE,
    )

    encname = encfsctl_result.stdout.decode().strip()
    return encname


@click.command('show-encoded-path')
@config_option
@click.argument('decoded-path')
def show_encoded_path(config: _Config, decoded_path: str) -> None:
    """
    Show the encfs encoded path given a decoded file path or name.
    """
    encoded_path = _encode_with_encfs(
        path_or_file_name=decoded_path,
        encfs_pass=config.encfs_pass,
        root_dir=config.remote_encrypted,
    )
    click.echo(encoded_path)


@click.command('show-decoded-path')
@config_option
@click.argument('encoded-path')
def show_decoded_path(config: _Config, encoded_path: str) -> None:
    """
    Show the encfs decoded path given an encoded file path or name.
    """
    decoded_path = _decode_with_encfs(
        path_or_file_name=encoded_path,
        encfs_pass=config.encfs_pass,
        root_dir=config.remote_encrypted,
    )
    click.echo(decoded_path)


@click.command('move-file-or-dir')
@config_option
@click.argument('src')
@click.argument('dst')
def move_file_or_dir(config: _Config, src: str, dst: str) -> None:
    """
    Move a file from source to destination.
    """
    encoded_src_path = _encode_with_encfs(
        path_or_file_name=src,
        encfs_pass=config.encfs_pass,
        root_dir=config.remote_encrypted,
    )
    encoded_dst_path = _encode_with_encfs(
        path_or_file_name=dst,
        encfs_pass=config.encfs_pass,
        root_dir=config.remote_encrypted,
    )

    rclone_src_path = _rclone_path(
        rclone_remote=config.rclone_remote,
        rclone_root=config.path_on_cloud_drive,
        rclone_relative_path=encoded_src_path,
    )
    rclone_dst_path = _rclone_path(
        rclone_remote=config.rclone_remote,
        rclone_root=config.path_on_cloud_drive,
        rclone_relative_path=encoded_dst_path,
    )

    move_args = [
        str(config.rclone),
        '--config',
        str(config.rclone_config_path),
        _rclone_verbosity_flag(verbose=config.rclone_verbose),
        'moveto',
        rclone_src_path,
        rclone_dst_path,
    ]
    subprocess.run(args=move_args, check=True)


@click.command('mkdir')
@config_option
@click.argument('path')
def mkdir(config: _Config, path: str) -> None:
    """
    Create a directory.
    """
    encoded_path = _encode_with_encfs(
        path_or_file_name=path,
        encfs_pass=config.encfs_pass,
        root_dir=config.remote_encrypted,
    )

    rclone_path = _rclone_path(
        rclone_remote=config.rclone_remote,
        rclone_root=config.path_on_cloud_drive,
        rclone_relative_path=encoded_path,
    )

    move_args = [
        str(config.rclone),
        '--config',
        str(config.rclone_config_path),
        _rclone_verbosity_flag(verbose=config.rclone_verbose),
        'mkdir',
        rclone_path,
    ]
    subprocess.run(args=move_args, check=True)


@click.command('cloud-drive-mount')
@config_option
def mount_cloud_storage(config: _Config) -> None:
    """
    Foreground mount which will keep remounting until unmount file exists.
    """
    _create_dirs(
        remote_encrypted=config.remote_encrypted,
        remote_decrypted=config.remote_decrypted,
        local_encrypted=config.local_encrypted,
        local_decrypted=config.local_decrypted,
        data_dir=config.data_dir,
    )

    _mount_cloud_storage(
        rclone_remote=config.rclone_remote,
        unmount_lock_file=config.unmount_lock_file,
        rclone=config.rclone,
        remote_encrypted=config.remote_encrypted,
        rclone_verbose=config.rclone_verbose,
    )


@click.command('check-config')
@config_option
def check_config(config: _Config) -> None:  # pylint: disable=unused-argument
    """
    Check some parts of the given configuration file and error if there is a
    problem.
    """


@click.command('wait-for-cloud-storage-mount')
@config_option
@click.pass_context
def wait_for_cloud_storage_mount(
    ctx: click.core.Context,
    config: _Config,
) -> None:
    """
    Wait for the cloud storage mount for a short while.

    Exit with an error if it is not ready within the expected time.
    """
    _wait_for_remote_mount(
        ctx=ctx,
        remote_encrypted=config.remote_encrypted,
        path_on_cloud_drive=config.path_on_cloud_drive,
    )


cloud_drive_tools.add_command(check_config)
cloud_drive_tools.add_command(mkdir)
cloud_drive_tools.add_command(mount_cloud_storage)
cloud_drive_tools.add_command(mount_data_dir)
cloud_drive_tools.add_command(move_file_or_dir)
cloud_drive_tools.add_command(show_decoded_path)
cloud_drive_tools.add_command(show_encoded_path)
cloud_drive_tools.add_command(sync_deletes)
cloud_drive_tools.add_command(unmount_all)
cloud_drive_tools.add_command(upload)
cloud_drive_tools.add_command(wait_for_cloud_storage_mount)

if __name__ == '__main__':
    cloud_drive_tools()
