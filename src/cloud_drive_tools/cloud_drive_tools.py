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
import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, Optional, Union

import click
import yaml

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@click.group(name='cloud-drive-tools')
def cloud_drive_tools() -> None:
    """
    Manage Plex tools.
    """


def _pre_command_setup(
    ctx: click.core.Context,
    config: Dict[str, str],
) -> None:
    message = (
        'Require a version of Python with a fix for '
        'https://bugs.python.org/issue35192'
    )
    if sys.version_info.major == 3:
        assert sys.version_info.minor >= 5, message

    if sys.version_info.major == 3 and sys.version_info.minor == 5:
        assert sys.version_info.micro >= 4, message

    if sys.version_info.major == 3 and sys.version_info.minor == 6:
        assert sys.version_info.micro >= 2, message

    encfs6_config = str(config['encfs6_config'])
    os.environ['ENCFS6_CONFIG'] = encfs6_config

    rclone_binary = Path(config['rclone'])
    plexdrive_binary = Path(config['plexdrive'])

    dependencies = (
        rclone_binary,
        plexdrive_binary,
        'unionfs-fuse',
        'encfs',
        'fusermount',
        'screen',
    )
    for dependency in dependencies:
        if shutil.which(str(dependency)) is None:
            message = '"{dependency}" is not available on the PATH.'.format(
                dependency=dependency,
            )

            ctx.fail(message=message)


def _validate_config(
    ctx: click.core.Context,
    param: Union[click.core.Option, click.core.Parameter],
    value: Optional[Union[int, bool, str]],
) -> Dict[str, str]:
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
            'plexdrive',
            'rclone',
            'rclone_config_path',
            'rclone_remote',
        ],
    )
    optional_keys = set(['http_proxy', 'https_proxy'])

    allowed_keys = {*required_keys, *optional_keys}

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

    return config


def config_option(command: Callable[..., None]) -> Callable[..., None]:
    """
    Click option for passing a configuration file.
    """
    default_config_path = Path('vars.yaml')

    function = click.option(
        '--config',
        '-c',
        type=click.Path(exists=True),
        callback=_validate_config,
        default=str(default_config_path),
        help='The path to a file including configuration YAML.',
    )(command)  # type: Callable[..., None]
    return function


def _local_cleanup(config: Dict[str, str]) -> None:
    """
    Delete local data older than "days_to_keep_local" from the configuration
    file.
    """
    days_to_keep_local = float(config['days_to_keep_local'])
    mount_base = Path(config['mount_base'])
    local_decrypted = mount_base / 'local-decrypted'

    message = (
        'Deleting local files older than "{days_to_keep_local}" days old'
    ).format(days_to_keep_local=days_to_keep_local)

    LOGGER.info(message)

    seconds_to_keep_local = days_to_keep_local * 24 * 60 * 60

    file_paths = local_decrypted.rglob('*')

    now_timestamp = datetime.datetime.now().timestamp()
    oldest_acceptable_time = now_timestamp - seconds_to_keep_local

    for path in file_paths:
        ctime = path.stat().st_ctime
        if path.is_file() and ctime < oldest_acceptable_time:
            path.unlink()


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
        message = 'Cannot unmount "{mountpoint}" - it is not mounted'.format(
            mountpoint=str(mountpoint),
        )
        LOGGER.warning(msg=message)
        return

    message = 'Unmounting "{mountpoint}"'.format(mountpoint=str(mountpoint))
    LOGGER.info(msg=message)
    unmount_args = ['fusermount', '-u', str(mountpoint)]
    subprocess.run(args=unmount_args, check=True)


def _unmount_all(config: Dict[str, str]) -> None:
    message = 'Unmounting all ACDTools mountpoints'
    LOGGER.info(message)

    data_dir = Path(config['data_dir'])
    mount_base = Path(config['mount_base'])
    remote_encrypted = mount_base / 'acd-encrypted'
    remote_decrypted = mount_base / 'acd-decrypted'
    local_encrypted = mount_base / 'local-encrypted'
    unmount_lock_file = Path(__file__).parent / 'unmount.acd'

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
@click.pass_context
def unmount_all(ctx: click.core.Context, config: Dict[str, str]) -> None:
    """
    Unmount all mountpoints associated with ACDTools.
    """
    _pre_command_setup(ctx=ctx, config=config)
    _unmount_all(config=config)


@click.command('upload')
@config_option
@click.pass_context
def upload(ctx: click.core.Context, config: Dict[str, str]) -> None:
    """
    Upload local data to the cloud.
    """
    _pre_command_setup(ctx=ctx, config=config)

    rclone_binary = Path(config['rclone'])
    rclone_config_path = Path(config['rclone_config_path'])

    upload_pid_file = Path(__file__).parent / 'upload.pid'
    if upload_pid_file.exists():
        running_pid = upload_pid_file.read_text()
        if running_pid:
            proc_file = Path('/proc') / running_pid
            if proc_file.exists():
                message = 'Upload script already running'
                LOGGER.error(msg=message)
                ctx.fail(message=message)

    encfs_pass = str(config['encfs_pass'])
    current_pid = os.getpid()
    upload_pid_file.write_text(str(current_pid))
    _sync_deletes(config=config)

    rclone_remote = 'Google'

    mount_base = Path(config['mount_base'])
    remote_encrypted = mount_base / 'acd-encrypted'
    local_encrypted = mount_base / 'local-encrypted'
    path_on_cloud_drive = config['path_on_cloud_drive']

    # Determine the .unionfs-fuse directory name as to not upload it
    exclude_name_args = [
        'encfsctl',
        'encode',
        '--extpass',
        'echo {encfs_pass}'.format(encfs_pass=encfs_pass),
        str(remote_encrypted),
        '.unionfs-fuse',
    ]

    exclude_name_result = subprocess.run(
        args=exclude_name_args,
        check=True,
        stdout=subprocess.PIPE,
    )
    exclude_name = exclude_name_result.stdout.decode()

    upload_args = [
        str(rclone_binary),
        '--config',
        str(rclone_config_path),
        '-v',
        'copy',
    ]
    if exclude_name:
        upload_args += [
            '--exclude',
            '/{exclude_name}/*'.format(exclude_name=exclude_name),
        ]

    upload_args += [
        str(local_encrypted),
        '{rclone_remote}:{path_on_cloud_drive}'.format(
            rclone_remote=rclone_remote,
            path_on_cloud_drive=path_on_cloud_drive,
        ),
    ]

    children = str(local_encrypted.glob('*'))
    upload_attempts = 0

    if children:
        while subprocess.run(args=upload_args, check=False).returncode != 0:
            upload_attempts += 1
            message = (
                'Some uploads failed - uploading again after a sync '
                'sync (attempt {upload_attempts})'
            ).format(upload_attempts=upload_attempts)
            LOGGER.error(msg=message)

            if upload_attempts >= 5:
                message = 'Upload failed 5 times - giving up'
                ctx.fail(message=message)
    else:
        message = '{local_encrypted} is empty - nothing to upload'.format(
            local_encrypted=str(local_encrypted),
        )
        LOGGER.info(msg=message)

    message = 'Upload Complete - Syncing changes'
    LOGGER.info(message)
    _local_cleanup(config=config)
    upload_pid_file.unlink()


def _sync_deletes(config: Dict[str, str]) -> None:
    mount_base = Path(config['mount_base'])
    remote_encrypted = mount_base / 'acd-encrypted'
    local_decrypted = mount_base / 'local-decrypted'
    search_dir = local_decrypted / '.unionfs-fuse'

    rclone_binary = Path(config['rclone'])
    rclone_config_path = Path(config['rclone_config_path'])
    rclone_remote = 'Google'

    encfs_pass = str(config['encfs_pass'])
    path_on_cloud_drive = config['path_on_cloud_drive']

    if not (search_dir.exists() and search_dir.is_dir()):
        message = 'No .unionfs-fuse/ directory found, nothing to delete'
        LOGGER.info(message)
        return

    hidden_flag = '_HIDDEN~'
    matched_files = search_dir.rglob(pattern='*' + hidden_flag)

    failed_sync_deletes = False

    for matched_file in matched_files:
        filename = matched_file.name
        assert filename.endswith(hidden_flag)
        filename = filename[:-len(hidden_flag)]
        encfsctl_args = [
            'encfsctl',
            'encode',
            '--extpass',
            'echo {encfs_pass}'.format(encfs_pass=encfs_pass),
            str(remote_encrypted),
            '"{filename}"'.format(filename=filename),
        ]

        encfsctl_result = subprocess.run(
            args=encfsctl_args,
            check=True,
            stdout=subprocess.PIPE,
        )

        encname = encfsctl_result.stdout

        if not encname:
            message = 'Empty name returned from encfsctl - skipping.'
            LOGGER.error(message)
            failed_sync_deletes = True
            continue

        rclone_path = '{rclone_remote}:{path_on_cloud_drive}/{encname}'.format(
            rclone_remote=rclone_remote,
            path_on_cloud_drive=path_on_cloud_drive,
            encname=encname.decode().strip(),
        )

        message = 'Attempting to delete "{rclone_path}"'.format(
            rclone_path=rclone_path,
        )
        LOGGER.info(message)

        rclone_args = [
            str(rclone_binary),
            '--config',
            str(rclone_config_path),
            'ls',
            '--max-depth',
            '1',
            rclone_path,
        ]
        rclone_output = subprocess.run(args=rclone_args, check=False)
        rclone_status_code = rclone_output.returncode
        if rclone_status_code:
            message = '{matched_file} is not on a cloud drive'.format(
                matched_file=str(filename),
            )
            LOGGER.info(message)
        else:
            message = '{matched_file} exists on cloud drive - deleting'.format(
                matched_file=str(filename),
            )
            LOGGER.info(message)

            rclone_delete_args = [
                str(rclone_binary),
                '--config',
                str(rclone_config_path),
                'delete',
                rclone_path,
            ]

            while subprocess.run(
                args=rclone_delete_args,
                check=False,
            ).returncode != 0:
                message = 'Delete failed, trying again in 30 seconds'
                LOGGER.error(message)
                time.sleep(30)

            message = '{matched_file} deleted from cloud drive'.format(
                matched_file=str(matched_file),
            )
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
@click.pass_context
def sync_deletes(ctx: click.core.Context, config: Dict[str, str]) -> None:
    """
    Reflect unionfs deleted file objects on Google Drive.
    """
    _pre_command_setup(ctx=ctx, config=config)
    _sync_deletes(config=config)


def _mount(ctx: click.core.Context, config: Dict[str, str]) -> None:
    mount_base = Path(config['mount_base'])
    cloud_drive_tools_path = Path(config['cloud_drive_tools_path'])
    remote_encrypted = mount_base / 'acd-encrypted'
    remote_decrypted = mount_base / 'acd-decrypted'
    local_encrypted = mount_base / 'local-encrypted'
    local_decrypted = mount_base / 'local-decrypted'
    data_dir = Path(config['data_dir'])

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
                'Directory "{directory}" already exists and an error was '
                'raised which we are ignoring.'
            ).format(directory=directory)

    encfs_pass = str(config['encfs_pass'])

    path_on_cloud_drive = config['path_on_cloud_drive']
    # pathlib.Path does not handle `///` well in a path.
    remote_mount = str(remote_encrypted) + '//' + path_on_cloud_drive

    message = 'Mounting cloud storage drive'
    LOGGER.info(message)
    _, config_file_path_str = tempfile.mkstemp()
    config_file_path = Path(config_file_path_str)
    config_contents = yaml.dump(data=config)
    config_file_path.write_text(config_contents)
    pid = os.getpid()
    screen_log_dir = Path('/var/log')
    screen_log_filename = 'cloud-drive-tools-screenlog.{pid}'.format(pid=pid)
    screen_log_path = screen_log_dir / screen_log_filename

    screen_args = [
        'screen',
        '-L',
        '-Logfile',
        str(screen_log_path),
        '-dm',
        '-S',
        'cloud-drive-tools-mount',
        str(cloud_drive_tools_path),
        'acd-cli-mount',
        '-c',
        str(config_file_path),
    ]

    subprocess.run(args=screen_args, check=True)

    # After `screen` starts it takes some time to mount the drive.
    attempts = 0
    while not os.path.exists(str(remote_mount)):
        attempts += 1
        if attempts > 5:
            message = 'Remote mount not found after 5 attempts, exiting'
            ctx.fail(message)

        message = ('Remote mount {remote_mount} does not exist yet, waiting.'
                   ).format(remote_mount=remote_mount)
        LOGGER.info(message)
        time.sleep(5)

    message = 'Mounting local encrypted filesystem'
    LOGGER.info(message)
    encfs_args = [
        'encfs',
        '--extpass',
        'echo {encfs_pass}'.format(encfs_pass=encfs_pass),
        '--reverse',
        str(local_decrypted),
        str(local_encrypted),
    ]
    subprocess.run(args=encfs_args, check=True)

    message = 'Mounting cloud decrypted filesystem'
    LOGGER.info(message)
    encfs_args = [
        'encfs',
        '--extpass',
        'echo {encfs_pass}'.format(encfs_pass=encfs_pass),
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
        '{local_decrypted}=RW:{remote_decrypted}=RO'.format(
            local_decrypted=str(local_decrypted),
            remote_decrypted=str(remote_decrypted),
        ),
        str(data_dir),
    ]
    subprocess.run(args=unionfs_fuse_args, check=True)


@click.command('mount')
@click.option(
    '--no-unmount',
    is_flag=True,
    help='Do not unmount before trying to mount filesystems.',
)
@config_option
@click.pass_context
def mount(
    ctx: click.core.Context,
    config: Dict[str, str],
    no_unmount: bool,
) -> None:
    """
    Mount necessary directories.
    """
    _pre_command_setup(ctx=ctx, config=config)
    if not no_unmount:
        _unmount_all(config=config)
    _mount(ctx=ctx, config=config)


def _acd_cli_mount(config: Dict[str, str]) -> None:
    unmount_lock_file = Path(__file__).parent / 'unmount.acd'
    mount_base = Path(config['mount_base'])
    remote_encrypted = mount_base / 'acd-encrypted'
    plexdrive_binary = Path(config['plexdrive'])

    while not unmount_lock_file.exists():
        message = 'Running cloud storage mount in the foreground'
        LOGGER.info(message)
        _unmount(mountpoint=remote_encrypted)
        plexdrive_args = [
            str(plexdrive_binary),
            'mount',
            '-o',
            'allow_other,read_only',
            '-v',
            '2',
            str(remote_encrypted),
        ]

        subprocess.run(args=plexdrive_args, check=True)

        message = (
            'Cloud storage mount exited - checking if to remount in a couple '
            'of seconds'
        )
        LOGGER.info(message)
        time.sleep(2)

    message = 'The acdcli mount exited cleanly'
    LOGGER.info(message)
    unmount_lock_file.unlink()


@click.command('acd-cli-mount')
@config_option
@click.pass_context
def acd_cli_mount(ctx: click.core.Context, config: Dict[str, str]) -> None:
    """
    Foreground mount which will keep remounting until unmount file exists.
    """
    _pre_command_setup(ctx=ctx, config=config)
    _acd_cli_mount(config=config)


cloud_drive_tools.add_command(acd_cli_mount)
cloud_drive_tools.add_command(mount)
cloud_drive_tools.add_command(sync_deletes)
cloud_drive_tools.add_command(unmount_all)
cloud_drive_tools.add_command(upload)

if __name__ == '__main__':
    cloud_drive_tools()
