..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
Expose persistent serial numbers for local disks
================================================

https://blueprints.launchpad.net/nova/+spec/local-disk-serial-numbers

It is possible to assign a serial number to virtual hard disks which can be
queried by the guest operating system. We currently do this for attached
volumes, but we don't do it for local disks: local root disks, ephemerals, or
swap disks.

The primary user-facing purpose of this feature is to expose a persistent
serial number for local disks to guests.


Problem description
===================

The presentation of disks to a guest operating system is inherently
non-deterministic. The most robust way to address disks is by some persistent
property of the disk, serial number being the most convenient. The problem is
most acute for attached volumes, and we already expose the volume id as the
serial number of a disk. For robustness and consistency we should extend this
feature to cover local disks.

Use Cases
---------

As a user running windows guests, I need to avoid having activation issues due
to a lack of a stable disk serial number.

As an admin, I need to be able to migrate windows guests to address maintenance
needs in the datacenter without risking de-activating customer windows
instances because disk serial numbers are not stable.

As a user, I want a common mechanism to identify both attached volumes
and ephemeral disks for my workload.


Proposed change
===============

This spec proposes a new contract with virt drivers. For drivers which
implement stable local disk serial numbers, the following will be true:

* Local root disks, ephemeral, and swap disks will all have a serial number.

* This serial number will not change for the lifetime of an instance.

* For tagged disks, this serial number will be exposed to the guest in device
  metadata.

The method used to generate and persist local disk serial numbers is not
defined, and may differ between drivers as long as the above remain true. For
example, the ironic driver would meet the first 2 points automatically by the
virtue of physical disks having persistent and stable serial numbers. The
ironic driver can implement this spec simply by exposing these serial numbers
in device metadata for tagged local disks.

The spec proposes a specific scheme to implement the above for the libvirt
driver, which may also be of use to other virt drivers.

All disks attached to an instance, except config disks, have a block device
mapping, which has a persistent uuid. We will present this uuid to the
guest as the serial number of local disks. For volumes we will continue to
present volume id as we do currently.

Serial numbers will be exposed to virt drivers by adding a serial field to
DriverBlockDevice. This will additionally require us to expose the block device
mapping of local root disks to virt drivers, which we do not currently do. We
will do this by adding an additional field to the block_device_info dict,
meaning that existing drivers which know nothing about this field will not be
affected by it.

Alternatives
------------

Other ways to generate a persistent serial number for local disks were
considered. These included:

* Using a combination of instance uuid and a driver-specific disk identifier

* Using a combination of instance uuid and bdm id

The former was rejected as being driver-specific. The latter was rejected as it
would change should we ever implement the ability to migrate between cells.


Data model impact
-----------------

A uuid field was added to BDMs during Queens for this feature. To complete this
process, in the Stein cycle we should add a not null constraint to the uuid
field, and remove python code which handles null uuid fields in the database.

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

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None

Developer impact
----------------

None.

Upgrade impact
--------------

block_device_mapping.uuid will become not nullable. The online migration which
populates this column merged in Queens in change I4b33751b. This schema change
will fail unless operators have executed online migrations.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mbooth@redhat.com

Work Items
----------

* Expose local root disks to virt drivers via block_device_info.

* Add serial field to DriverBlockDevice with the existing behaviour for
  volumes, and the new bdm uuid for local disks.

* Update libvirt driver to use DriverBlockDevice.serial for all disks.


Dependencies
============

None.


Testing
=======

Unit testing should cover:

* block_device_info contains root disk for both boot-from-volume and local
  root.

* DriverVolumeBlockDevice and its subclasses should contain a serial field
  containing the volume id.

* Other DriverBlockDevice subclasses should contain a serial field contining
  the BDM uuid.

Tempest testing should cover:

* Local disks presented to guest have a serial number if they are present in
  device metadata.


Documentation Impact
====================

This is a user-visible change. Documentation covering device tagging should be
updated to reflect the ability to tag local disks.

References
==========

None.


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - * Introduced
       * Merged addition of block_device_mapping.uuid
       * Partially merged exposing block_device_mapping.uuid to drivers
   * - Rocky
     - * Reproposed
   * - Stein
     - * Reproposed
