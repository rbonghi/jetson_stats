jtop
==========

.. currentmodule:: jtop

Installing
----------

jtop can be installed with `pip <https://pip.pypa.io>`_

.. code-block:: bash

  sudo -H pip3 install -U jetson-stats

Don't forget to **logout** or **reboot** your board

Running
-------

Simple and fast! You can write on your shell **jtop** and that's it!

.. code-block:: bash

  jtop

.. image:: images/jtop.png
   :align: center

Other options are available with `-h` option:

.. code-block:: console
  :class: no-copybutton

  nvidia@agx-orin:~/$ jtop -h
  usage: jtop [-h] [--no-warnings] [--restore] [--loop] [--color-filter] [-r REFRESH] [-p PAGE] [-v]

  jtop is system monitoring utility and runs on terminal

  optional arguments:
    -h, --help            show this help message and exit
    --no-warnings         Do not show warnings (default: False)
    --restore             Reset Jetson configuration (default: False)
    --loop                Automatically switch page every 5s (default: False)
    --color-filter        Change jtop base colors, you can use also JTOP_COLOR_FILTER=True (default: False)
    -r REFRESH, --refresh REFRESH
                          refresh interval (default: 500)
    -p PAGE, --page PAGE  Open fix page (default: 1)
    -v, --version         show program\'s version number and exit

You can change page using *left*, *right* arrow or *TAB* to change page.

Pages
^^^^^

**jtop** have four different pages to control your NVIDIA Jetson:

1. **ALL** Are collected all information about your board: CPUs status, Memory, *GPU*, disk, fan and all status about jetson_clocks, NVPmodel and other
2. **GPU** A real time GPU history about your NVIDIA Jetson
3. **CPU** A real time CPU plot of NVIDIA Jetson
4. **MEM** A real time Memory chart and swap monitor
5. **CTRL** Enable/Disable **jetson_clocks**, **nvpmodel** or **fan** directly from here
6. **INFO** All information about libraries, CUDA, Serial Number, interfaces, ...

Controls
^^^^^^^^

To control the your NVIDIA Jetson are available this keyboard commands:

In page **4 MEM**:

* **c** Clear cache
* **s** Enable/Disable extra swap
* **+** and **-** Increase and decrease swap size

In page **5 CTRL**:

* **a** Start/Stop jetson_clocks service (Note: jetson_clocks start only after 60s from up time)
* **e** Enable/Disable jetson_clocks on board boot
* **+** and **-** Increase and decrease the NVPmodel
* **f** Manual/jetson_clocks mode for your fan
* **p** and **m** Increase and decrease the Fan speed