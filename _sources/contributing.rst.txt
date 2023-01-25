✨ Contributing
================

jetson-stats is a community-maintained project and we happily accept contributions.

If you wish to add a new feature or fix a bug:

#. `Check for open issues <https://github.com/rbonghi/jetson_stats/issues>`_ or open
   a fresh issue to start a discussion around a feature idea or a bug. There is
   a *Contributor Friendly* tag for issues that should be ideal for people who
   are not very familiar with the codebase yet.
#. Fork the `jetson-stats repository on Github <https://github.com/rbonghi/jetson_stats>`_
   to start making your changes.
#. Write a test which shows that the bug was fixed or that the feature works
   as expected.
#. Send a pull request and bug the maintainer until it gets merged and published.

Setting up your developing environment
--------------------------------------

Clone and build in developer mode jetson-stats

.. code-block:: console

   git clone https://github.com/rbonghi/jetson_stats.git
   cd jetson_stats
   sudo pip3 install -v -e .

.. note::
   
   You can also testing on x86 machines, installing the emulation for *tegrastats*, *nvpmodel* and *jetson_clocks*

   .. code-block:: console

      sudo ./tests/develop.sh

   .. danger::

      Do not install on Jetson! Otherwise will overwrite your files.


Manually stop and disable jtop service
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to manually control the jtop service you need to disable the service and manually start one in a terminal,
following the commands below

.. code-block:: console

   sudo systemctl stop jtop.service
   sudo systemctl disable jtop.service

Now you can work running in your terminal the jtop service

.. code-block:: console

   sudo JTOP_SERVICE=True jtop --force

Restore jtop service
^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

   sudo systemctl enable jtop.service
   sudo systemctl start jtop.service

Test this package
-----------------

Before commit you can test jetson-stats on multiple python version and check if the documentation is built

This script works with docker, and you can quickly run it.

.. code-block:: console

   bash tests/local_test.sh

When you run this script will do:

1. Build and compile all python images (2.7,3.6,3.7,3.8,3.9.3.10,3.11)
2. Build documentation image (Sphinx)

There are different options:

.. code-block:: console
   :class: no-copybutton

   user@workstation:~/jetson_stats$ bash tests/local_test.sh --help
   Jetson_stats tox local test. USE ONLY IN A TEST DESKTOP MACHINE!
   Usage:
   tests/local_test.sh [options]
   options,
      -h|--help              | This help
      --debug                | Run image
      -py|--python [PYHTON]  | Set a specific python version, example PYTHON=3.9
      --doc                  | Run and build ONLY the documentation

Live docker with tox
^^^^^^^^^^^^^^^^^^^^

Run tox or work live from the terminal

.. code-block:: console

   bash tests/local_test.sh --debug -py 3.9 

Test documentation
^^^^^^^^^^^^^^^^^^

If you want to run **only** the documentation:

.. code-block:: console

   bash tests/local_test.sh --doc

Test GUI
^^^^^^^^

If you want to test or develop the GUI library

You can run this command from your terminal `python3 -m jtop.tests_gui.x` where **x** is the name of the file, example

.. code-block:: console

   python3 -m jtop.tests_gui.gui_page 

Releases
--------

- Announce intent to release on Discord, see if anyone wants to include last minute changes.
- Update ``jtop/__init__.py`` with the proper version number
- Commit the changes to a ``release-X.Y.Z`` branch.
- Create a pull request
- Release a new `tag <https://git-scm.com/book/en/v2/Git-Basics-Tagging>`_ will automatically generate a new version

.. code-block:: console
   :class: no-copybutton

   git tag -a <VERSION> -m <MESSAGE>