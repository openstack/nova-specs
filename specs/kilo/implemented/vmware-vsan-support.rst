..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
VMware: Support for vSAN Datastores
===================================

https://blueprints.launchpad.net/nova/+spec/vmware-vsan-support

Currently the vmwareapi compute driver only supports deploying instances to NFS
and VMFS datastores. This blueprint proposes to add support for using vSAN
storage as well.

Explanation of terminology used:

The term "datastore" as referred to in the spec and the driver refers to
the vSphere concept a logical storage container, a place where VM data (among
other things) is kept. The purpose of this abstraction is to provide a uniform
way for vSphere clients to access said VM data regardless of what hardware, I/O
protocols or transport protocols are used by the underlying storage.

All vSphere datastores until recently has been broadly divided into two types,
VMFS and NFS. The vmwareapi driver has been supporting the use of both since
its inception, without having to distinguish between either, largely because of
this datastore abstraction.

vSAN storage is a third type of datastore introduced in vSphere. It is
a software-defined distributed storage that aggregates disks (magnetic for
capacity, SSD for cache/performance) attached to a group of hosts into a
single storage pool. That pool is once again exposed as a single datastore.

Problem description
===================

Currently datastores with type "vsan" is ignored by compute driver entirely.
One obstacle to using this type of datastore is that virtual disk data files
(the "-flat.vmdk" files) are not directly addressable as datastore paths. Since
both the spawn and snapshot workflow in the vmware driver addresses the data
files in some way, they will have to be changed to support vSAN datastores.

Use Cases
----------

The End User will be able to use vSAN datastores and deploy streamOptimized
images.

Project Priority
-----------------

None

Proposed change
===============

The change is divided into two areas:

* Recognize and use datastores of a new type ("vsan").
* Update existing code involved in exporting and importing Glance images to
  use alternate vSphere APIs that does not address disk data files directly.

The second area of change is mainly provided by the image-transfer
functionality in the oslo.vmware library [*]_. The proposal is to update the
code to use said library.

However, the only disk format that these alternate APIs support is the
'streamOptimized' format. (The streamOptimized format is a sparse, compressed,
and stream-friendly version of the VMDK disk that is well suited for
import/export use cases, such as the glance<->hypervisor exchanges described
above). This implies that only streamOptimized disk images are deployable on
vSAN. The driver will be modified to recognize Glance vmdk images tagged
with the property vmware_disktype='streamOptimized' as disks of such format,
and only use the alternate APIs when handling disks of this format.

.. [*] To import a disk image to a vSAN datastore, oslo.vmware uses the
   ImportVApp vSphere API is used to import the image as a shadow virtual
   machine (a VM container to hold a reference to the base disk disk, and is
   not meant to be powered on). Likewise, to export the disk image, the library
   uses the ExportVM vSphere API.  These APIs do not reference the virtual disk
   data file paths directly and are hence compatible with vSAN storage.


Alternatives
------------

None.

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

There is a new configuration option under the [vmware] section,
"image_transfer_timeout_secs", which configures how long an image transfer can
proceed before timing out.

In order to deploy existing VMDK images to vSAN, these images will have to be
converted to streamOptimized and reimported to glance.


Developer impact
----------------

Minimal. The changes related to blueprint are mostly isolated in the areas of
handling a new vmdk format type and add recognition and use of an additional
datastore type called "vsan".

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  rgerganov

Work Items
----------

The work is broadly decomposed into:

* use oslo.vmware image_transfer module to handle download of images
* use oslo.vmware image_transfer module to handle upload of image snapshot
* update driver to allow the use of datastores of type vSAN.
* update driver to recognized a new vmdk format (streamOptimized)


Dependencies
============

None

Testing
=======

Since Tempest in general does not support driver-specific tests, the proposal
is to update the MineSweeper CI
(https://wiki.openstack.org/wiki/NovaVMware/Minesweeper), to provide
vCenter with vSAN storage and additional tests to verify existing Tempest
tests passes when invoked against compute nodes using it.


Documentation Impact
====================

New information in the vmware driver section of the Nova documentation will
have to be added to document:

* How to configure a compute node for vSAN use.
* The virtual disk format requirement ("streamOptimized" only) when using vSAN
  storage.
* The new "image_transfer_timeout_secs" configuration option.
* How to obtain a streamOptimized disk from a virtual machine or vmdk disk in a
  non-streamOptimized format.


References
==========

* https://github.com/openstack/oslo.vmware
* https://wiki.openstack.org/wiki/NovaVMware/Minesweeper
