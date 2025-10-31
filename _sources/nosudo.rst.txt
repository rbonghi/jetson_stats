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

   - Verifies whether ``pip3`` and ``pipx`` are installed; if either is missing, installs them via ``apt``.
   - Ensures ``~/.local/bin`` is on your ``PATH`` so that ``pipx`` applications are available in future shells.

3. **Install jtop via pipx**

   - Uses ``pipx install "git+https://github.com/rbonghi/jetson_stats.git"`` to install the latest version in an isolated user environment.
   - Determines the correct executable path (usually ``~/.local/bin/jtop`` or inside the pipx venv).

4. **Systemd service setup**

   - Creates or updates ``/etc/systemd/system/jtop.service`` to point to your user’s jtop binary.
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
   • Uses pipx’s isolation, making upgrades and uninstalls clean and safe
   • Fully compatible with Ubuntu 24.04+ and later Debian-based systems
   • Ensures jtop runs under your user account (avoids root-owned processes)
   • Provides systemd integration for automatic startup and recovery
