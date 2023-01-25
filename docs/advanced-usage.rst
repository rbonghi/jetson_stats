👨‍💻 Advanced Usage
=====================

.. currentmodule:: jtop

You can install jtop in a virtual environment or in a docker following the guidelines below

.. admonition:: Virtual environment

  If you need to install in a virtual environment like *virtualenv*, you **must** install before in your host **and after** in your environment, like:

  .. code-block:: bash

    virtualenv venv
    source venv/bin/activate
    pip install -U jetson-stats


**jtop** is a complete controller of all systems in your NVIDIA Jetson

* Tegrastats
* NVP Model
* Fan
* Status board (i.g. Model version, Jetpack, … )

.. code-block:: python
  
  from jtop import jtop


You can initialize the jtop node like a file i.g.

.. code-block:: python

  with jtop() as jetson:
      # jetson.ok() will provide the proper update frequency
      while jetson.ok():
          # Read tegra stats
          print(jetson.stats)

Or manually start up with the basic function open/close

.. code-block:: python

  jetson = jtop()
  jetson.start()
  stat = jetson.stats
  jetson.close()

You can read the status of your NVIDIA Jetson via callback

.. code-block:: python

  def read_stats(jetson):
      print(jetson.stats)

  # Open the jtop
  jetson = jtop()
  # Attach a function where you can read the status of your jetson
  jetson.attach(read_stats)
  jetson.loop_for_ever()

Other examples are available in `example folder <https://github.com/rbonghi/jetson_stats/tree/master/examples>`_.