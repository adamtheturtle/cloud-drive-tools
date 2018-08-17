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
* `plexdrive`
* `rclone`
* `rclone_remote`

and optionally:

* `http_proxy`
* `https_proxy`

For example:

```yaml
data_dir: "/home/data"
days_to_keep_local: 14
encfs6_config: "/home/encfs6.xml"
encfs_pass: "XXX"
mount_base: "/home/.mounts"
path_on_cloud_drive: "/Media"
plexdrive: "/home/plexdrive"
rclone: "/home/rclone-v1.37-linux-amd64/rclone"
rclone_remote: "Google"
```
