jetson-stats
============

.. toctree::
   :hidden:
   :maxdepth: 3

   rnext.it<https://rnext.it>
   Community Discord<https://discord.gg/BFbuJNhYzS>
   sponsors
   jtop
   advanced-usage
   docker
   reference
   other-tools/index
   contributing

.. toctree::
   :hidden:
   :caption: Project

   ros_jetson_stats<https://github.com/rbonghi/ros_jetson_stats>
   ros2_jetson_stats<https://github.com/NVIDIA-AI-IOT/ros2_jetson_stats>


jetson-stats is a package for monitoring and control your NVIDIA Jetson [Orin, Xavier, Nano, TX] series. Works with all NVIDIA Jetson ecosystem.

.. image:: images/jtop.gif
   :align: center

Installing
----------

jetson-stats can be installed with `pip <https://pip.pypa.io>`_

.. code-block:: bash

   sudo -H pip3 install -U jetson-stats

**🚀 That's it! 🚀** 

Don't forget to **logout** or **reboot** your board


Usage
-----

The :doc:`jtop` is the place to go to learn how to use the the core tool and monitoring your board.
The more in-depth :doc:`advanced-usage` guide is the place to jtop such a python library and use for your project.

.. code-block:: python

   from jtop import jtop

   with jtop() as jetson:
      # jetson.ok() will provide the proper update frequency
      while jetson.ok():
         # Read tegra stats
         print(jetson.stats)

The :doc:`reference` documentation provides API-level documentation.


Compatibility
-------------

jetson-stats is compatible with:

* NVIDIA Jetson Orin Series
   * NVIDIA Jetson AGX Orin
* NVIDIA Jetson Xavier Series
   * NVIDIA Jetson AGX Xavier Industrial
   * NVIDIA Jetson AGX Xavier
   * NVIDIA Jetson Xavier NX
* NVIDIA Jetson Nano
* NVIDIA Jetson TX Series
   * NVIDIA Jetson TX2 NX
   * NVIDIA Jetson TX2i
   * NVIDIA Jetson TX2
   * NVIDIA Jetson TX1

If you need a specific Compatibility open an `issue <https://github.com/rbonghi/jetson_stats/issues/new?assignees=&labels=enhancement&template=feature_request.md&title=>`_.


License
-------

jetson-stats is made available under the AGPL-3.0 license. For more details, see `LICENSE <https://github.com/rbonghi/jetson_stats/blob/master/LICENSE>`_.


Contributing
------------

We happily welcome contributions, please see :doc:`contributing` for details.