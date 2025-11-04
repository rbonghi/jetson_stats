🧩 How it works
===============

The ``install_jtop_torun_without_sudo.sh`` script automates a safe,
user-friendly installation of **jtop** that allows you to run it without
``sudo``. It performs the following steps:

1. **Safety check**

   - Refuses to run if invoked as ``root`` or via ``sudo``.
   - Instructs you to run ``sudo -v`` first so that later privileged
     commands (``apt``, ``systemctl``) can execute without repeated password prompts.

2. **Prepare environment**

   - Verifies whether ``pip3`` and ``uv`` are installed; if either is missing, installs them via ``apt``.
   - Ensures ``~/.local/bin`` is on your ``PATH`` so that ``uv`` applications are available in future shells.

3. **Install uv. Then install jtop with uv**

   - Uses uv pip install --python ""$HOME/.local/share/jtop/bin/python" --upgrade "git+https://github.com/rbonghi/jetson_stats.git"
   - to install the latest jtop version in the user's environment.


4. **Systemd service setup**

   - Creates or updates ``/etc/systemd/system/jtop.service`` to point to /usr/local/bin/jtop.
   - Can now be run with or without sudo.
   - Sets safe defaults (``Restart=on-failure``, ``RestartSec=10s``, etc.) to make the service robust.

5. **Enable and start the service**

   - Reloads systemd, enables ``jtop.service`` to start automatically at boot,
     and restarts it immediately.

6. **Result**

   After installation, you can simply launch jtop from your terminal
   as a normal user (no ``sudo`` required):

   .. code-block:: bash

      jtop


Why use this method
===================

.. code-block:: text

   • Keeps the system (root) Python environment clean and untouched
   • Uses uv’s isolation, making upgrades and uninstalls clean and safe
   • Fully compatible with Ubuntu 24.04+ and later Debian-based systems
   • Ensures jtop runs under your user account (avoids root-owned processes)
   • Provides systemd integration for automatic startup and recovery
