🆘 Troubleshooting
==================

Let's resolve here the common issues can happening using jetson-stats (jtop).

Before to start, have you updated jetson-stats to the latest release?

if not, write:

.. code-block:: bash

  sudo pip3 install -U jetson-stats

If nothing changed follow the help below.

pip3: command not found
^^^^^^^^^^^^^^^^^^^^^^^

When you try to install jetson-stats, you read an output like:

.. code-block:: console
  :class: no-copybutton

  user@board:~$ sudo pip3 install -U jetson-stats
  sudo: pip3: command not found

you can simple install python3-pip

.. code-block:: bash

  sudo apt install python3-pip

jtop.service inactive
^^^^^^^^^^^^^^^^^^^^^

When the *jtop.service* (or previously *jetson-stats.service*) is inactive there are few different reasons

First step, restart jtop service following the command below

.. code-block:: bash

  sudo systemctl restart jtop.service

If the error is not fixed run:

.. code-block:: bash

  journalctl -u jtop.service -n 100 --no-pager

If you read here an error, open an `issue <https://github.com/rbonghi/jetson_stats/issues/new?assignees=&labels=bug&template=bug-report.md&title=>`_ reporting the output.

jtop start only with sudo
^^^^^^^^^^^^^^^^^^^^^^^^^

If jtop start only with ``sudo jtop`` and when you run without sudo you read this error:

.. code-block:: console
  :class: no-copybutton

  user@board:~$ jtop
  I can't access jtop.service.
  Please logout or reboot this board.

The reason can be your user is not allowed to have access to jtop.

There are two way to fix it:

1. Run the command below and check if is all **OK** if you read **FAIL** on fix permissions, press **Fix all** and logout/login.

.. code-block:: bash

    sudo jtop --health

.. image:: images/jtop-fail-user.png
  :align: center

1. You can manually do writing the command below

.. code-block:: bash

    sudo usermod -a -G jtop  $USER

remember to logout/login.

Bad visualization on Putty
^^^^^^^^^^^^^^^^^^^^^^^^^^

If you experiences a bad visualization working with jtop on Putty, like a sequence of "qqqqqwqqqq and xxxx" you can fix following the steps below:

1. Window -> Translation
2. Enable VT100 line drawing even in UTF-8 mode

Nothing fix my error
^^^^^^^^^^^^^^^^^^^^

Before to open an `issue`_, try to reinstall the latest version with this command

.. code-block:: bash

  sudo pip3 install --no-cache-dir -v -U jetson-stats

Save the output somewhere, if this command doesn't fix can be helpful when you one an `issue`_.

Run this command and save the output. This output help me to understand the reason of this error.

.. code-block:: bash

  journalctl -u jtop.service -n 100 --no-pager

Remember also to add other information about your board

You can find on:

.. code-block:: bash

  jetson_release -v

- jetson-stats version: [e.g. 1.8]

- P-Number: [e.g. pXXXX-XXXX]
- Module: [e.g. NVIDIA Jetson XXX]

- Jetpack: [e.g. 4.3]
- L4T: [e.g. 5.2.1]
