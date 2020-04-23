# cloud-drive-tools

Tooling for managing encrypted files on cloud drives.

Inspired by https://github.com/msh100/ACDTools.

Set up a YAML file `vars.yaml` with the following keys:

* `data_dir`
* `days_to_keep_local`
* `encfs6_config`
* `encfs_pass`
* `mount_base`
* `path_on_cloud_drive`
* `rclone`
* `rclone_remote`

and optionally:

* `http_proxy`
* `https_proxy`

The optional values currently do nothing.

For example:

```yaml
data_dir: "/home/data"
days_to_keep_local: 14
encfs6_config: "/home/encfs6.xml"
encfs_pass: "XXX"
mount_base: "/home/.mounts"
path_on_cloud_drive: "/Media"
rclone: "/home/rclone-v1.37-linux-amd64/rclone"
rclone_config_path: "/root/.config/rclone/rclone.conf"
rclone_remote: "Google"
cloud_drive_tools_path: "/root/.local/bin/cloud-drive-tools"
```

## Installing

Requires Python 3.6.2+, or 3.7+.
We require specific versions to avoid https://bugs.python.org/issue35192.

This can be installed with ``pip``, or ``pipsi``.

For example on Ubuntu 18.04, install `pipsi`:

```sh
apt install -y python3-pip python3-venv
pip3 install virtualenv
curl https://raw.githubusercontent.com/bjoernpollex/pipsi/prefer-venv/get-pipsi.py | python3
echo "export PATH=/root/.local/bin:$PATH" >> ~/.bashrc
. ~/.bashrc
```

Then install `cloud-drive-tools`:

```sh
git clone https://github.com/adamtheturtle/cloud-drive-tools.git /home/cloud-drive-tools
pipsi install /home/cloud-drive-tools
```
