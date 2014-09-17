..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Libvirt - Start LXC from a block device
==========================================

https://blueprints.launchpad.net/nova/+spec/libvirt-start-lxc-from-block-devices

The purpose of this blueprint is to enable the LXC containers
to be started from a block device volumes.

Problem description
===================

Currently, LXC containers can only be started from a Glance image.
However, a minor adjustment is needed to support it's being booted
using a block volume as its root OS filesystem.

Proposed change
===============

Separate the lxc disk handling code from _create_domain() to
_lxc_disk_handler context manager. It will use block_device_mapping
to map the device that instance has been started from, otherwise,
an image will be used.

The _lxc_disk_handler will handle the "pre" and "post" lxc start actions
on the disk, to mount it and clean the lxc namespace, after it starts.
These actions are specific to LXC, both for images and volumes.

The following layout of the volumes will be supported.

 - Unpartitioned, filesystem across entire content.
 - Partitioned. Only mount the filesystem in the first partition.
   In case there are more than one partition present, only the first one
   will be considered, while others will be ignored.

The user may create a volume from and existing Glance image and boot
LXC container in one command:

    nova boot --flavor FLAVOR --block-device source=image,id=ID,dest=volume,\
              size=SIZE,shutdown=PRESERVE,bootindex=0 NAME

or booting the LXC container from an existing volume

    nova boot --flavor FLAVOR --block-device source=volume,id=ID,dest=volume,\
              size=SIZE,shutdown=PRESERVE,bootindex=0 NAME


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
As LXC will always share the host's kernel, between all instanances,
any vulnerability in the kernel, maybe used to harm the host.
In general, the kernel's filesystem drivers should be trusted to
free of vulnerabilities that the user filesystem image may exploit.

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
Vladik Romanovsky <vladik.romanovsky@enovance.com>

Work Items
----------
 - Introduce a _lxc_disk_handler context manager method and
   separate all lxc disk handling code from _create_domain()
   to it.
 - Add logic to the _lxc_disk_handler to mount the volumes,
   using the provided block_device_mapping
 - Remove the lxc specific mapping creation in blockinfo.py

Dependencies
============
None

Testing
=======

None


Documentation Impact
====================

None

References
==========

[1] https://review.openstack.org/#/c/74537
