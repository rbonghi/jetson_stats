How is it works
===============

How works jtop

.. image:: /images/architecture.drawio.png
   :align: center

jtop.sock
---------

jtop use a service to sharing the data between client (jtop gui or your python script) and a server.

This service, called ``jtop.service`` use a socket file. It is located in:

.. code-block:: console
  :class: no-copybutton

  /run/jtop.sock

This socket is protected by access mode: **660** equivalent to ``srw-rw----`` and by the group.

Only other users in ``jtop`` have access to this socket
