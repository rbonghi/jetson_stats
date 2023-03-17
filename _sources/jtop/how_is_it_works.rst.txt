How is it works
===============

jtop is a power monitor that use a service and a python client library.

.. image:: /images/architecture.drawio.png
   :align: center

Like the image above, when jtop service start, load and decode the information on your board.

Initialization
--------------

#. Read NVIDIA Jetson EEPROM to detect which NVIDIA Jetson is running
#. decode jetson_clocks to know if is running and which engines are involved when it start.
#. decode the NVPmodel to know which model is selected
#. Open the ``/run/jtop.sock`` socket and wait a jtop client connection

Loop
----

When jtop is running read all status from your current board and share all this data to all jtop python connections.

#. Read and estimate the CPU utilization from ``/proc/stat``
#. Read status from all devices in ``/sys/devices/system``
#. Read and decode memory status from ``/proc/meminfo``
#. Decode and read status from all swap using ``swapon`` command
#. Check status from jetson_clocks
#. Check which nvpmodel is running

jtop.sock
---------

jtop use a service to sharing the data between client (jtop gui or your python script) and a server.

This service, called ``jtop.service`` use a socket file. It is located in:

.. code-block:: console
  :class: no-copybutton

  /run/jtop.sock

This socket is protected by access mode: **660** equivalent to ``srw-rw----`` and by the group.

Only other users in ``jtop`` **group** have access to this socket
