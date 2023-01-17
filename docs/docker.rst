Docker
======

.. currentmodule:: jtop

You can run directly in Docker jtop, you need only to:

1. Install jetson-stats on your **host**
2. Install on your container jetson-stats as well
3. Pass to your container `/run/jtop.sock:/run/jtop.sock`

You can try running this command

.. code-block:: bash

  docker run --rm -it -v /run/jtop.sock:/run/jtop.sock rbonghi/jetson_stats:latest

Design your Dockerfile
----------------------

.. code-block:: docker

  FROM python:3-buster
  RUN pip install -U jetson-stats

