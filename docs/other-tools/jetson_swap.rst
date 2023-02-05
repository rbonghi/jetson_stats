jetson_swap
===========

Simple manager to switch on and switch off a swapfile in your jetson.

.. code-block:: bash

    jetson_swap

All options available

.. code-block:: console
  :class: no-copybutton

  nvidia@jetson-nano:~$ sudo jetson_swap -h
  usage: jetson_swap [-h] [-d DIRECTORY] [-n NAME] [-s SIZE] [-a] [-t] [--off]

  Create a swap file and enable on boot (require sudo)

  optional arguments:
    -h, --help            show this help message and exit
    -d DIRECTORY, --dir DIRECTORY
                          Directory to place swapfile (default: )
    -n NAME, --name NAME  Name swap file (default: swapfile)
    -s SIZE, --size SIZE  Size in Gigabytes (default: 8)
    -a, --auto            Enable swap on boot (default: False)
    -t, --status          Check if the swap is currently active (default: False)
    --off                 Switch off the swap (default: False)
