..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Hyper-V: Fibre channel support
==========================================

https://blueprints.launchpad.net/nova/+spec/hyperv-fibre-channel

This blueprint proposes adding Fibre Channel support for the Hyper-V driver.

Problem description
===================

At the moment, the Hyper-V driver supports attaching volumes only via iSCSI
or SMB. In many cases, using FC based topologies might be desired.

Use Cases
----------

This blueprint addresses deployers possessing FC based infrastructure.

This will enable attaching volumes exported by Cinder FC based backends using
the retrieved target informations such as WWN and LUN.


Proposed change
===============

A new volume driver will be introduced, having a workflow similar to the iSCSI
volume driver. This means that the volumes will be attached to the instances
as pass-through disks, making this transparent to the guest.

Alternatives
------------

An alternative would be exposing virtual HBAs to guests. Although this has
some benefits in terms of performance, it requires the guest to take part in
the volume attach proccess.

Also, another limitation is that this scenario would be supported only in case
of Windows Server guests.

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

This will enable using high performance FC based storage.

Other deployer impact
---------------------

The deployer will be responsible of properly configuring the HBA.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  plucian

Work Items
----------

* Implement the Fibre Channel volume driver

Dependencies
============

None

Testing
=======

This will be tested by the Hyper-V CI.

Documentation Impact
====================

This feature will be documented.

References
==========

None

History
=======

None
