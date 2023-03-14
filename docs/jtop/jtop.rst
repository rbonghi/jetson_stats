📊 jtop
=======

.. currentmodule:: jtop

jtop can be installed with `pip <https://pip.pypa.io>`_

.. code-block:: bash

  sudo pip3 install -U jetson-stats

Don't forget to **logout/login** or **reboot** your board

Run jtop
--------

Simple and fast! You can write on your shell **jtop** and that's it!

.. code-block:: bash

  jtop

.. image:: /images/jtop.png
   :align: center

Other options are available with ``-h`` option:

.. code-block:: console
  :class: no-copybutton

  nvidia@agx-orin:~$ jtop -h
  usage: jtop [-h] [--no-warnings] [--restore] [--loop] [--color-filter] [-r REFRESH] [-p PAGE] [-v]

  jtop is system monitoring utility and runs on terminal

  optional arguments:
    -h, --help            show this help message and exit
    --health              Status jtop and fix (default: False)
    --error-log           Generate a log for GitHub (default: False)
    --no-warnings         Do not show warnings (default: False)
    --restore             Reset Jetson configuration (default: False)
    --loop                Automatically switch page every 5s (default: False)
    --color-filter        Change jtop base colors, you can use also JTOP_COLOR_FILTER=True (default: False)
    -r REFRESH, --refresh REFRESH
                          refresh interval (default: 500)
    -p PAGE, --page PAGE  Open fix page (default: 1)
    -v, --version         show program\'s version number and exit

You can change page using *left*, *right* arrow or *TAB* to change page.

If you want to know how is ti works, check  this menu below:

.. toctree::
    how_is_it_works

Pages
-----

**jtop** have four different pages to control your NVIDIA Jetson:

1. **ALL** Are collected all information about your board: CPUs status, Memory, *GPU*, disk, fan and all status about jetson_clocks, NVPmodel and other
2. **GPU** A real time GPU history about your NVIDIA Jetson
3. **CPU** A real time CPU plot of NVIDIA Jetson
4. **MEM** A real time Memory chart and swap monitor
5. **ENG** A real time list with the status of all engines
6. **CTRL** Enable/Disable **jetson_clocks**, **nvpmodel** or **fan** directly from here
7. **INFO** All information about libraries, CUDA, Serial Number, interfaces, ...

ALL
^^^

.. image:: /images/pages/01-jtop.png
   :align: center

In this page are summarized all information about your board.

#. **CPU** For each CPU in this page the color is the percentage of utilization of: *(summarized page 3)*
    - Green - user
    - Yellow - nice
    - Red - system
#. **Memory** Each bar describe the status of your device *(summarized page 4)*
    a. Memory - RAM status
        - Cyan - Used memory
        - Green - GPU shared memory
        - Blue - Buffers memory
        - Yellow - Cached memory
    b. Swap
        - Red - Swap memory
        - Yellow - Cached swap memory
    c. EMC (if available)
        - Frequency EMC
        - percentage bandwidth used at Frequency
    d. Iram (if available)
#. **System** In this section are collected many info about *(summarized page 6)*
    - Fan speed and RPM
    - Status jetson_clocks (if available)
    - Status NVPmodel (if available)
#. **GPU** Current GPU status *(summarized page 2)*
#. **Disk** Disk space utilization
#. **GPU processes** GPU processes
   You can sort the table clicking on each title on the page
#. **HW Engines** (If available) all engines running on your board *(summarized page 5)*
#. **Temperatures** Status temperatures of your devices
    - If Yellow warning zone over 84 degree
    - If red critical zone over 100 degree
#. **Power** Status *(summarized page 6)*
    - For each rail there are instantaneous Power and average power
    - The last power in bold is the total or estimated total

GPU
^^^

.. image:: /images/pages/02-jtop.png
   :align: center

In this page the GPU status. A detailed documentation of this output is available at :py:attr:`jtop.jtop.gpu` 

#. **GPU** In this chart are collected many information about the integrated GPU, starting from the title:
    - iGPU (integrated GPU)
    - name GPU
    - Load percentage
    - Governor GPU
#. **GPU Shared RAM** Status Shared GPU. (In grey the used memory)
#. **Flags** GPU Flags
    - **3D Scaling** You can enable and disable the 3D scaling on your board
    - **Railgate**
    - **Power control**
    - **TPC PG** (for NVPmodel)
#. **GPU Frequency** This bar show the the minimum and maximum Frequency and on right side the current Frequency. Can be also available the GPC frequency
#. **GPU processes** GPU processes
   You can sort the table clicking on each title on the page

CPU
^^^

.. image:: /images/pages/03-jtop.png
   :align: center

In this page there is the CPU status of each core. A detailed documentation of this output is available at :py:attr:`jtop.jtop.cpu`

#. **ALL** Collected status from all CPU
#. **Core** For each core there is a chart with load and governor
#. **Model** CPU model processor
#. **CPU Frequency** This bar show the the minimum and maximum Frequency and on right side the current Frequency.

MEM
^^^

.. image:: /images/pages/04-jtop.png
   :align: center

Memory and Swap, From this page you can also enable/disable a new swap or clean the cache. A detailed documentation of this output is available at :py:attr:`jtop.jtop.memory`



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

Options
-------

There are different options available for jtop

Health
^^^^^^

If something goes wrong, you can check the ``jtop`` status with

.. code-block:: bash

  sudo jtop --health

.. image:: /images/jetson_config-02-jtop.png
   :align: center

This tool, will check and fix:

- **jetson-stats** - Fix jetson-stats service
- **Permissions** - Fix permissions for your user
- **variables** - Check if are installed all variables :doc:`/other-tools/environment_variables`

Restore
^^^^^^^

If you want to restore the original board configuration you can simply write

.. code-block:: bash

  jtop --restore

.. image:: /images/jtop-restore.png
   :align: center

This command will restore the original configuration of:

- ``jetson_clocks``
- fan
- ``nvpmodel``
- jtop configuration

Color filter
^^^^^^^^^^^^

This option change the red color for text and background to blue.

To enable this feature you can add this option

.. code-block:: bash

  jtop --color-filter

or you can add in your ``.bashrc``

.. code-block:: bash

  JTOP_COLOR_FILTER=True

The output will be like the image below

.. image:: /images/jtop-color-filter.png
   :align: center

Error-log
^^^^^^^^^

If your board is not included, jetpack missing, hardware missing, you can launch this script

.. code-block:: bash

  jtop --error-log

This script generate a file ``jtop-error.log`` ready to be attached on your issue