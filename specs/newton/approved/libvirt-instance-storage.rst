..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Persist libvirt instance storage metadata
=========================================

https://blueprints.launchpad.net/nova/+spec/libvirt-instance-storage

Libvirt ephemeral storage layout is currently mostly inferred based on the
local configuration of the compute node. This is problematic in several cases.
In edge cases, it has been the recent cause of several severe security
vulnerabilities. It also makes storage configuration hard or impossible to vary
between compute nodes in the same installation, or over time after
installation. By persisting storage metadata of a particular instance
explicitly we make its configuration unambiguous and simple to understand, and
therefore less vulnerable to security issues. We also make it possible to
unambiguously represent multiple storage configurations within a single
installation. While we don't make the necessary changes to correctly handle
multiple storage configurations, by describing them unambiguously we lay a
foundation for future work to enable this.


Problem description
===================

There are several problems with the libvirt ephemeral storage code:

- The code has been expanded beyond its original design with the addition of
  each new backend type (LVM/RBD/ploop), but has never been redesigned to
  accomodate these substantially different models.

- Storage layout is inferred from 2 config variables on the compute node:
  libvirt.images_type and use_cow_images. An instance which was created on
  another compute node with different values for these config variables, or
  which was created before the values of these config variables were changed,
  will be incorrectly handled. This will lead to failure at best. At worst it
  will create a security vulnerability.

- The imagebackend code uses a single method, cache(), to create both disks
  from glance images, and disks from templates (i.e. blank filesystems or swap
  disks). These are then handled differently by different backends. Writing to
  the image cache is done by the individual backends, which use the image cache
  differently due to their different natures. To do this, backends must
  differentiate between glance images and templates, but the interface does not
  permit them to do this directly. The Raw backend greps 'image_id' from the
  argument passed to its template function. The LVM backend uses
  'ephemeral_size'. The Ploop backend uses 'context' and 'image_id', and
  independently fetches glance metadata. The cache() interface needs to be
  changed to reflect its usage.

- The cache() interface does not provide the backend with any metadata about
  disk image it is being given to import. Consequently it must either infer it
  heuristically or inspect it. Both methods are prone to error and potential
  security bugs. The replacement for cache() must allow the backend to
  determine in advance the format and size of the disk it is importing.

- The Raw backend is badly named, as disks using the Raw backend may be either
  raw or qcow2. The Raw backend first inspects the disk it is importing (see
  problem above), then writes its format to a local file called disk.info.
  Storing the format of the disk means that there is no need to inspect the
  disk at boot time, which prevents a severe security flaw. However, we can do
  much better than this. disk.info is used inconsistently between the Qcow2 and
  Raw backends, and other backends do not use it at all. It is also local to a
  single compute node, so cannot be used to determine storage layout during a
  migration.

Use Cases
---------

Developer: Reduce bugs, in particular security bugs, by creating a single,
canonical, persistent repository for disk metadata.

Developer: Enable future backend development work by removing poorly understood
heuristics and tight coupling.

Developer: By storing disk layout per instance rather than compute node, enable
the future development of features to:

- migrate between disk layouts.

- implement different per-instance storage policies (e.g. SSD vs spinning
  rust).

- track the process of upgrading disk layouts during an upgrade.

Proposed change
===============

We need to make 2 changes:

1 Split the cache() method into 2 separate methods:
  create_from_image(image_id), and create_from_func(func, size).

2 Create a persistent record of a disk's layout before creating the disk. This
  includes at least: the backend in use, disk format, and size. This persistent
  record must be extensible so that, for example, in the future we can specify
  multiple local storage locations for qcow2 disks, and choose between them.

The first change involves a substantial refactoring of libvirt's imagebackend
module. This should be achieved with a minimum of functional change.

The second change depends on the first. With the first change in place we have
enough context when creating a disk to know how big it is, what format it is,
and where it should go. We will implement library code which persists this
information for the disk, and then calls out to the relevant backend. It will
be stored in a virt driver specific field we will add to BlockDeviceMapping:
driver_info. Higher level code will treat this as an opaque blob. The libvirt
driver will treat it as a serialised versioned object: LibvirtDiskMetadata.
LibvirtDiskMetadata will initially contain the metadata mentioned above.

Alternatives
------------

There are undoubtedly other ways to achieve this. The important principal,
though, is that the driver should have a persistent, unambiguous record of how
an instance's storage is laid out. I have picked this one.

Data model impact
-----------------

A driver_info column will be added to the block_device_mapping table with type
Text. The column will be nullable, and will initially be unpopulated. It will
not be indexed, or have any associated constraints.

The column will be populated by the driver when performing any operation on a
disk and it is found to be unpopulated. It will initially take values based on
the current behaviour of the driver.

REST API impact
---------------

None

Security impact
---------------

This change does not directly impact security, but by simplifying an area of
code which has been the source of several severe security bugs it should
indirectly improve security. Specifically, by ensuring we always know the
format of a virtual disk we should never have to perform insecure format
inspection.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

When reading block device mappings for the driver, we will need to additionally
pull back driver_info, which will add some small overhead. More significantly,
with this change the driver will update the BlockDeviceMapping object for each
disk during boot and similar operations. We should be able to reduce the impact
of this update for instances with multiple disks by batching them in a single
update to a BlockDeviceMappingList object. This would require only one round
trip to conductor.

Other deployer impact
---------------------

None

Developer impact
----------------

The change adds a driver_info field to the BlockDeviceMapping object, and uses
it in the libvirt driver. Other drivers may also use this field, although this
change does not define how they should do that.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mbooth-9

Other contributors:
  None

Work Items
----------

- Refactor libvirt.imagebackend to split up cache()

- Add persistent metadata storage in BlockDeviceMapping


Dependencies
============

None


Testing
=======

Primarily, this should introduce **no functional change**. Its purpose is to
enable future change. Consequently, to the greatest extent possible, all
existing tests should continue to run with a minimum of change.

Tempest should require no changes.

Unit tests will likely have significant churn due to changing internal
interfaces, but the scenarios covered should be at least the same as
previously.

Note that Jenkins currently only tests the Qcow2 and Rbd(ceph) backends
in the gate. All current libvirt tempest jobs run by Jenkins use the
default Qcow2 backend except gate-tempest-dsvm-full-devstack-plugin-ceph, which
uses Rbd. We additionally coverage of the ploop backend in
check-dsvm-tempest-vz7-exe-minimal run by Virtuozzo CI. This means that we
currently have no gate coverage of the Raw and Lvm backends.


Documentation Impact
====================

None

References
==========

None


History
=======

None
