jetson_swap
===========

Simple manager to switch on and switch off a swapfile in your jetson.

.. code-block:: bash

    jetson_release

All options available

.. code-block:: bash
  :class: no-copybutton

    nvidia@jetson-nano:~/$ sudo jetson_swap -h
    usage: createSwapFile [[[-d directory ] [-s size] -a] | [-h] | [--off]]
    -d | --dir    <directoryname> Directory to place swapfile
    -n | --name   <swapname> Name swap file
    -s | --size   <gigabytes>
    -a | --auto   Enable swap on boot in /etc/fstab 
    -t | --status Check if the swap is currently active
    --off         Switch off the swap
    -h | --help   This message
