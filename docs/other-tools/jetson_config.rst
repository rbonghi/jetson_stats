jetson_config
=============

Check jetson-stats health, enable/disable desktop, enable/disable jetson_clocks,
improve the performance of your wifi are available only in one click using jetson_config

.. code-block:: bash

    sudo jetson_config

.. image:: /images/jetson_config-01-main.png
   :align: center

**jetson_config** have different pages

- **Health** - Check the status of jetson-stats
- **Update** - Update this tool to the latest version
- **Desktop** - Enable/Disable boot from desktop
- **About** - Information about this configuration tool

Health
------

This page help to self check this package and automatically fix broken parts, there are these submenus:

- **jetson-stats** - Fix jetson-stats service
- **Permissions** - Fix permissions for your user
- **variables** - Check if are installed all variables :doc:`environment_variables`

.. image:: /images/jetson_config-02-jtop.png
   :align: center

Desktop
-------

This menu enable and disable the Desktop on your jetson.

**Remember ssh require a login to work**

.. image:: /images/jetson_config-03-desktop.png
   :align: center

