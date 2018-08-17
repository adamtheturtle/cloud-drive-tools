# cloud-drive-tools

Tooling for managing encrypted files on cloud drives.

Inspired by https://github.com/msh100/ACDTools.

Set up a YAML file `vars.yaml` with the following keys:

`data_dir`
`days_to_keep_local`
`encfs6_config`
`encfs_pass`
`mount_base`
`path_on_cloud_drive`
`plexdrive`
`rclone`
`rclone_remote`

and optionally:

`http_proxy`
`https_proxy`
