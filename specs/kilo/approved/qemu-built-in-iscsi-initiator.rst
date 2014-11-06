..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Add support for QEMU built-in iSCSI initiator
=============================================

https://blueprints.launchpad.net/nova/+spec/qemu-built-in-iscsi-initiator

QEMU has built-in iSCSI initiator using libiscsi and Libvirt can handle it as
same as other network storages. This blueprint adds iSCSI support to Nova's
network volume driver (nova.virt.libvirt.LibvirtNetVolumeDriver).


Problem description
===================

Nova already has iSCSI volume driver for KVM/QEMU
(nova.virt.libvirt.LibvirtISCSIVolumeDriver), but iSCSI targets for volumes
aren't attached to VMs directly but to the host OS of nova-compute nodes. It
means:

* Storage structure of the host OS will be changed when volumes are attaching
  to / detaching from VMs on the host. The commands executed by nova-compute to
  attach/detach volumes are complex. So they may cause confusing storage
  structure the host OS and make trouble shooting difficult when a problem had
  occured.

* The host OS have many system logs on attaching/detaching volumes and tons of
  error logs if a trouble occurs at the iSCSI target or multipath.

* The VMs on a compute node will be stopped when an iSCSI volume is attached or
  detached to a VM and it causes the host OS crash.

Use Cases
----------

* Using so many iSCSI-based volumes and attached them to many VMs on a host.
  Say that up to 50 VMs on a host and up to 20 volumes attached to a VM.  It
  means that the host OS will handle up to 1k iSCSI targets by itself with
  LibvirtISCSIVpolumeDriver and the number will be 2x, 3x, or 4x if you use
  iSCSI multipath capability.

Project Priority
-----------------

None


Proposed change
===============

Using KVM/QEMU built-in iSCSI initiator via Libvirt for attaching iSCSI
volumes. To do so, we have to implement 2 functionality:

* Implement a new libvirt XML configuration handler class named
  LibvirtConfigSecret. It manages information for iSCSI CHAP authentication.

* Extend LibvirtNetVolumeDriver to support QEMU built-in iSCSI initiator using
  LibvirtConfigSecret if needed.

Alternatives
------------

Just use LibvirtISCSIVolumeDriver.

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

* QEMU built-in iSCSI initiator doesn't support multipath capability. So VMs
  will be not able to handle volumes when iSCSI connections die even if the
  backend iSCSI storage has multipath capability.

* QEMU binary of Ubuntu 14.04 doesn't have iSCSI support. Users have to install
  libiscsi2 package and libiscsi-dev from Debian and rebuild QEMU binary
  with libiscsi support by themselves.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Akira Yoshiyama <akirayoshiyama@gmail.com>

Work Items
----------

Working patches exist, so we have to:

* Implement unit tests.
* Review the codes.


Dependencies
============

None


Testing
=======

Usually, devstack builds an OpenStack deployment with Cinder using
LVMISCSIDriver, so we can use it for basic smoke tests. And we should do more
tests with vendor iSCSI drivers.


Documentation Impact
====================

Adding configuration notes to use the driver like below:

To use this, you have to write a parameter at nova.conf:

  volume_drivers = iscsi=nova.virt.libvirt.volume.LibvirtNetVolumeDriver,
                   iser=nova.virt.libvirt.volume.LibvirtISERVolumeDriver,...

or just

  volume_drivers = iscsi=nova.virt.libvirt.volume.LibvirtNetVolumeDriver


References
==========

* Libvirt Secret XML format:
  http://libvirt.org/formatsecret.html

* Libvirt Domain XML format: Hard drives, floppy disks, CDROMs
  http://libvirt.org/formatdomain.html#elementsDisks
