..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
VMware Ephemeral Disk Support
=============================

https://blueprints.launchpad.net/nova/+spec/improve-vmware-disk-usage

The blueprint adds support for support ephemeral disks to the VMware driver.

Problem description
===================

The VMware driver does not support ephemeral disks.

Use Cases
----------

Driver parity. All virt driver should implement the same set of basic
features (including ephemeral disks). So that when a user uses Nova
they don't have to worry about which virt driver they are using if
they are using basic features.

Project Priority
-----------------

None

Proposed change
===============

The change will add ephemeral disk support to the VMware driver. The commit
acec2579b796d101f732916bfab557a66cebe512 added in a method create_virtual_disk.
This method will be used to create the ephemeral disk for the instance.

The method will create an ephemeral disk for the instance on the datastore.
This will be done according to the size defined in the instance flavor.

Alternatives
------------

* Do not implement the feature.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

* Users will be able to use ephemeral disks for the vCenter driver.

Performance Impact
------------------

A modest increase in network traffic will slow down spawn operations as we
create the ephemeral disk, size it, and place it for mounting in the vSphere
virtual machine.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  garyk
  heut2008

Work Items
----------

* refactor and port https://review.openstack.org/#/c/51793/ for Kilo

Dependencies
============

blueprint vmware-spawn-refactor

Testing
=======

* Minesweeper tests involving ephemeral disks will be turned on or written


Documentation Impact
====================

After this blueprint the vmware driver will support ephemeral disks. This will
need some additional documentation and changes to supported feature lists.

References
==========

None
