..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Ironic virt driver: static portgroups support
=============================================

https://blueprints.launchpad.net/nova/+spec/ironic-portgroups-support

To allow the utilization of NIC aggregation when instance is spawned on
hardware server. Bonded NICs should be picked with higher preference
than single NICs. It will allow user to increase performance
or provide higher reliability of network connection.

Problem description
===================

To guarantee high reliability/increase performance of network connection
to an instance when it is spawned on a hardware server, link `aggregation`_
should be used.

Use Cases
---------

The operators want to use different bonding strategies to increase
reliability or performance of network connection to instance.

Proposed change
===============
Nova will call into ironic to get the list of ports of each portgroup
that has a VIF associated with it along with portgroup parameters,
and update network metadata with the needed information.

- Bump the ironic API version to get ironic support for portgroups.
- Generate network metadata in ironic virt driver and add all the additional
  info there (such as bond mode, transmit hash policy, MII link monitoring
  interval, and of which links the bond consists). Pass it into
  InstanceMetadata that will be used afterwards to generate the config drive.

Alternatives
------------

- Always use single NICs, do not care about bonding.

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

Instance network performance or reliability is increased, depending on
bonding model that is used.

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
  <vsaienko>

Other contributors:
  <vdrok>

Work Items
----------

- Bump the ironic client API version to give us something that can use
  portgroups.
- Generate network metadata  in ironic virt driver and add all the additional
  info there (such as bond mode, transmit hash policy, MII link monitoring
  interval, and of which links the bond consists). Pass it into
  InstanceMetadata that will be used afterwards to generate the config drive.


Dependencies
============

* `Ironic ml2 integration`_
* `Ironic plug unplug vifs`_

Testing
=======

Add bonding module to cirros. The ironic team has manually tested a cirros
image re-built with bonding modules enabled, and it works as expected.
Update ironic CI to use portgroups to test them.

Documentation Impact
====================

None

References
==========

None

.. _`aggregation`: https://www.kernel.org/doc/Documentation/networking/bonding.txt
.. _`ironic ml2 integration`: https://specs.openstack.org/openstack/ironic-specs/specs/not-implemented/ironic-ml2-integration.html
.. _`ironic plug unplug vifs`: https://blueprints.launchpad.net/nova/+spec/ironic-plug-unplug-vifs-update
