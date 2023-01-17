Advanced Usage
==============

.. currentmodule:: jtop

YOu can install jtop in a virtual environment or in a docker following the guidelines below

Virtual environment
-------------------

If you need to install in a virtual environment like *virtualenv*, you **must** install before in your host **and after** in your environment, like:

.. code-block:: bash

  virtualenv venv
  source venv/bin/activate
  pip install -U jetson-stats


Docker
----------

You can run jtop from a docker container, but you **must** install jetsons-stats as well on your host! Try with the command below:

.. code-block:: bash

  docker run --rm -it -v /run/jtop.sock:/run/jtop.sock rbonghi/jetson_stats:latest

or you can add in your Dockerfile writing:

.. code-block:: docker

  FROM python:3-buster
  RUN pip install -U jetson-stats