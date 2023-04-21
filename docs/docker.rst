🐋 Docker
=========

.. currentmodule:: jtop

You can run directly in Docker jtop, you need only to:

1. Install jetson-stats on your **host**
2. Install jetson-stats on your container as well
3. Pass to your container ``/run/jtop.sock:/run/jtop.sock``

You can try running this command

.. code-block:: bash

  docker run --rm -it -v /run/jtop.sock:/run/jtop.sock rbonghi/jetson_stats:latest

Design your Dockerfile
----------------------

.. code-block:: docker

jetson-stats need few things to be installed on your container.

1. apt-get install -y python3
2. ``apt-get install -y python3-pip`` or you can install from **source**

Below a simple example to install jetson-stats

  FROM python:3-buster
  RUN pip install -U jetson-stats

Tips and tricks
---------------

If you work with different **multiple users** on your docker container:

.. code-block:: bash

  docker run --group-add $JTOP_GID --rm -it -v /run/jtop.sock:/run/jtop.sock rbonghi/jetson_stats:latest

You can get the ``JTOP_GID`` by running:

.. code-block:: bash

  getent group jtop | awk -F: '{print $3}'

Issue reference `391 https://github.com/rbonghi/jetson_stats/issues/391`_