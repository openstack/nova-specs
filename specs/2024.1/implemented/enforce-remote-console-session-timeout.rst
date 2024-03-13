..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Enforce remote console session timeout
==========================================

https://blueprints.launchpad.net/nova/+spec/enforce-remote-console-session-timeout

Currently providing vnc console consists 3 parts:

1 - Working Conosle for Nova instance.
  Once a Nova instance is created in the hypervisor, the hypervisor
  itself provides a console without the need for additional installations
  within the instnace (as per nova.conf).
  To access the console, operators can use `virsh console instance-xxx`,
  which provides a serial console (character terminal access) and prompts
  the instance login console.

2 - Provide console access outside compute node via browser.
  When user creates a console URL to access console via a web browser.

    $ openstack console URL show <vm>

  The cmd calls Nova API, the Nova API in turn, communicates through the
  RPC to compute service, which returns a new URL for connecting to an
  existing console.

  The command does not create a new console but rather generates
  a URL for connecting to the existing console. This URL includes a token
  for authentication via the proxy.

  This URL can be used to connect to the Nova instance console. The console
  token is used to athenticate with the proxy, enabling new sessions to be
  established until the token ttl expires.
  The existing session continue to function even after token expiration until
  the tcp connection is closed.

3- Controller's Nova Proxy: Bridging Client Browser and Compute Node
  When a user connects to the provided URL via a browser, the Nova Proxy acts
  as an intermediary. It establishes a WebSocket connection to the hypervisor
  and proxies the console to the client.
  For VNC consoles, the Nova Proxy serves an HTML page with a JavaScript
  application that runs at client side in the user's browser, providing
  a VNC client experience.
  In the case of a serial console, the Nova Proxy provides a direct
  WebSocket connection without a pre-built client, allowing users to
  create their own clients that interact with the WebSocket.

::

                              [ Nova API, Compute, virt driver ]
  [client browser] <======>                                       <======> [target virtual machine]
                                  [ Nova proxy ]

                                Controller Node                                 Compute Node


Problem description
===================

Today, there is no mechanism in place to enforce the termination of a console
session when the console token expires. Users can continue to access the
console beyond the token expiration, and there is a need to address this
behavior to enhance security measures.

Use Cases
---------

- As an operator, I want to make sure that with console authentication TTL,
  console sessions get closed too, and hence the user should get
  disconnected from the console automatically.

Proposed change
===============

Implement a timer mechanism to automatically close target socket connection
from server side when token has expired based on exact token expiration
time. This will interrupt the real time console session on client side
browser or other application.

Also, introduce a new consoleauth config option `enforce_session_timeout`
that allows operator to enable or disable the token expiry check.
The default setting is disabled, with `False` as its default value. This
gives flexibility to exisiting console user based on their specific
requirements.


Alternatives
------------

- Client-side polling to check for token expiration. But as there are
  many vnc clients, its better to address the issue at server side
  to ensure a consistency in session timeout.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

This change enable strict time span for console access requiring,
While it doesn't inherently enhance the safety of console access,
it ensures that users must reauthenticate after a specified time
period.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

A new optional config option will be added.

Developer impact
----------------

None

Upgrade impact
--------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  auniyal


Feature Liaison
---------------

Feature liaison:
  auniyal


Work Items
----------

- Update Nova webproxy code
- tests

Dependencies
============

None

Testing
=======

- funtional


Documentation Impact
====================

- release notes

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2024.1 Caracal
     - Introduced
