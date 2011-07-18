===========================================================
 EventSocket - Socket wrapper for libevent TCP applications
===========================================================

:Version: 0.1.4
:Download: http://pypi.python.org/pypi/py_eventsocket
:Source: https://github.com/agoragames/py-eventsocket
:Keywords: python, mocking, testing, unittest, unittest2

.. contents::
    :local:

Overview
========

EventSocket is a wrapper around standard Python sockets that provides a simple callback API for handling reading, accepting, closures and errors. It is built specifically for TCP sockets, though it may be compatible with any socket family that uses ``send`` and ``recv`` (i.e. not UDP).

Examples
========

See the ``scripts`` directory for examples of how to use EventSocket. 

http_client
  A client which runs simultaneous requests to an http server. Mimics behavior of ``siege``, though it only supports a few options.

proxy
  A simple proxy which forwards data from localhost to another ``host:port``. Shows examples of setting up a server socket, handling an incoming connection and socket closures.

Installation
============

To install using ``pip``,::

    $ pip install py-eventsocket

If installing from source:

* with development requirements (e.g. testing frameworks) ::

    pip install -r development.txt

* without development requirements ::

    pip install -r requirements.txt


Bug tracker
===========

If you have any suggestions, bug reports or annoyances please report them
to our issue tracker at https://github.com/agoragames/py-eventsocket/issues

License
=======

This software is licensed under the `New BSD License`. See the ``LICENSE.txt``
file in the top distribution directory for the full license text.

.. # vim: syntax=rst expandtab tabstop=4 shiftwidth=4 shiftround
