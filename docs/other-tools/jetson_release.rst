jetson_release
==============

The command show the status and all information about your NVIDIA Jetson

.. code-block:: bash

    jetson_release

.. image:: /images/jetson_release.png
   :align: center

Options available

.. code-block:: console
    :class: no-copybutton

    nvidia@jetson-nano:~$ jetson_release --help
    Software part of jetson-stats 4.2.0 - (c) 2026, Raffaello Bonghi
    usage: jetson_release [-h] [-v] [-s]

    Show detailed information about this board. Machine, Jetpack, libraries and
    other

    optional arguments:
    -h, --help     show this help message and exit
    -v, --verbose  Show all variables (default: False)
    -s, --serial   Show serial number (default: False)
