..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
VNC console support for Ironic driver
=========================================================

https://blueprints.launchpad.net/nova/+spec/ironic-vnc-console

The feature aims at providing a vnc console from Ironic.

Problem description
===================
End users often have to troubleshoot their instances because they might
have broken their boot configuration or locked themselves out with a
firewall. Keyboard-Video-Mouse (KVM) access is often required for
troubleshooting these types of issues as serial access is not always
available or correctly configured. Also, KVM provides a better user
experience as compared to serial console.

Horizon's VNC console is not supported for the ironic
nodes provisioned by Nova. This spec intends to extend that to
graphical console via the novnc proxy.

Use Cases
---------

The end user will be able to get workable vnc console url from baremetal
server:
switch console type on bm side to ``vnc``
``openstack baremetal node console enable``
``openstack console url show --novnc``

nova_novncproxy should be deployed

Proposed change
===============

* the Ironic virt driver will have to implement ``get_vnc_console`` and return
  a ``ctype.ConsoleVNC`` with the required connection information
  (port/ip). Will raise ``ConsoleTypeUnavailable`` if vnc console
  is unavailable for the instance.
  To get the vnc console the ``node.get_console`` ironic API will be used (the
  same API that is used for serial console).


Alternatives
------------

Accept this limitation and only offer a serial console.
We can configure kvm access including access to the bios via the
serial proxy and shell in a box for nova provisioned ironic baremetal
instances.

Use out-of-band KVM access provided by administrator without Ironic support.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

The VNC connection to the nodes are secured by a token generated while
creating the console in Nova.
This bearer token is the only thing required to connect to the proxy,
So the connection between user and proxy should be protected via ssl
the same as with vms

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

most changes will be on ironic side. In ironic we have to choose which
console will be used serial or vnc. This choice does not affect nova.
On ironic side also will be implemented vnc proxy, to handle rfb handshake

additions to configs will be similar as for serial console:
``nova-novncproxy/nova.conf``:
[vnc]
novncproxy_host = ...
novncproxy_port = ...
server_listen = ...
server_proxyclient_address = ...
auth_schemes = vnc

``nova-compute-ironic/nova.conf``:
[vnc]
enabled = true
novncproxy_host = ...
novncproxy_port = ...
server_listen = ...
server_proxyclient_address = ...
novncproxy_base_url = ...

``nova-conductor/nova.conf``
[vnc]
novncproxy_host = ...
novncproxy_port = ...
server_listen = ...
server_proxyclient_address = ...

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
  kirillgermanov

Other contributors:
  None

Feature Liaison
---------------

None

Work Items
----------

* nova-compute-ironic: add new method ``get_vnc_console`` to Ironic virt
  driver

Dependencies
============

https://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/vnc-graphical-console.html#id2

Testing
=======

Add related unit test

Documentation Impact
====================
update required

https://docs.openstack.org/nova/latest/admin/remote-console-access.html
https://docs.openstack.org/ironic/latest/admin/console.html

References
==========

* https://blueprints.launchpad.net/nova/+spec/ironic-vnc-console  - nova blueprint

* https://review.opendev.org/c/openstack/ironic/+/860689 - gerrit review ironic

* https://review.opendev.org/c/openstack/nova/+/863177 - gerrit review nova

* https://stackoverflow.com/questions/16469487/vnc-des-authentication-algorithm

History
=======

None
