..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Hyper-V serial console log
==========================================

https://blueprints.launchpad.net/nova/+spec/hyper-v-console-log

This blueprint introduces serial console log in the Nova Hyper-V driver.

Problem description
===================

The Hyper-V driver is currently not providing a serial console log unlike
other compute drivers (e.g. libvirt). This feature is particularly useful
for the troubleshooting of both Linux and Windows instances.

Proposed change
===============

Console log support in the Hyper-V nova driver will be obtained by implementing
the "get_console_output" method inherited from nova.virt.driver.ComputeDriver.

Hyper-V supports virtual serial ports in the guests, which can be redirected
to a dedicated named pipe on the host.

The driver will setup and connect the pipe upon starting or resuming a VM and
closing it when stopping, suspending or live migrating.

Data read from the pipe will be written in a file placed in the instance
directory, capped to a maximum size.

In case of live migration the console file must be moved to the destination
server.

A call to "get_console_output" for a given instance will return the content of
the file.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

None

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

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  petrutlucian94

Other contributors:
  alexpilotti

Work Items
----------

* Hyper-V Nova driver feature implementation
* Unit tests

Dependencies
============

None

Testing
=======

* Unit tests
* Additional Tempest tests can be evaluated

Documentation Impact
====================

None

References
==========

* Initial discussion (Juno design summit):
  https://etherpad.openstack.org/p/nova-hyperv-juno
