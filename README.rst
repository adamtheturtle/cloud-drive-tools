cloud-drive-tools
=================

Tooling for managing encrypted files on cloud drives.

Inspired by https://github.com/msh100/ACDTools.

Set up a YAML file ``vars.yaml`` with the following keys:

-  ``data_dir``
-  ``days_to_keep_local``
-  ``encfs6_config``
-  ``encfs_pass``
-  ``max_retries_remote_mount``
-  ``mount_base``
-  ``path_on_cloud_drive``
-  ``rclone``
-  ``rclone_remote``

For example:

.. code:: yaml

   cloud_drive_tools_path: "/root/.local/bin/cloud-drive-tools"
   data_dir: "/home/data"
   days_to_keep_local: 14
   encfs6_config: "/home/encfs6.xml"
   encfs_pass: "XXX"
   max_retries_remote_mount: 10
   # Set max retries higher if rclone takes a long time to mount.
   mount_base: "/home/.mounts"
   path_on_cloud_drive: "/Media"
   rclone: "/home/rclone-v1.37-linux-amd64/rclone"
   rclone_config_path: "/root/.config/rclone/rclone.conf"
   rclone_remote: "Google"
   # With verbose set to true, we can see which particular Google error is
   # occurring on a transfer.
   rclone_verbose: true

Installing
----------

Requires Python 3.6.2+, or 3.7+.
We require specific versions to avoid https://bugs.python.org/issue35192.

This can be installed with ``pip``, or ``pipsi``.

For example on Ubuntu 18.04, install ``pipsi``:

.. code:: sh

   apt install -y python3-pip python3-venv
   pip3 install virtualenv
   curl https://raw.githubusercontent.com/bjoernpollex/pipsi/prefer-venv/get-pipsi.py | python3
   echo "export PATH=/root/.local/bin:$PATH" >> ~/.bashrc
   . ~/.bashrc

Then install ``cloud-drive-tools``:

.. code:: sh

   git clone https://github.com/adamtheturtle/cloud-drive-tools.git /home/cloud-drive-tools
   pipsi install /home/cloud-drive-tools
