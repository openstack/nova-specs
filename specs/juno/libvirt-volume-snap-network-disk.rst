..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Volume Snapshots for Network-Backed Disks
==========================================

https://blueprints.launchpad.net/nova/+spec/libvirt-volume-snap-network-disk

Nova currently supports creating and deleting snapshots of file-backed
Cinder volumes via libvirt's snapshot mechanism.  This work extends
that capability to create and delete snapshots for network-backed disks
in a similar fashion.

This enables more complete Cinder volume functionality for deployments using
qemu network-backed volumes through a mechanism like libgfapi.


Problem description
===================

Nova does not support creating a snapshot via libvirt for a network-backed
Cinder volume that is attached to an instance.  Currently, attempting to
snapshot a Cinder volume configured this way will result in a failed snapshot
operation.

This is important for deployers who use qemu network-backed storage for Cinder
volumes.  (Typically for performance reasons.)


Proposed change
===============

Nova needs to be able to construct a <domainsnapshot> XML entity with
the required fields to snapshot a network-backed disk via libvirt.

Nova similarly needs to be able to pass in arguments for libvirt's
blockCommit and blockRebase operations to delete snapshots for network-backed
disks.  libvirt is adding support for a different style of parameters to the
blockjob APIs to support this, which allows referencing an existing item in
the disk snapshot change by index rather than by path name.

Alternatives
------------

There is no alternative for deployers wishing to use Nova-assisted snapshots
of Cinder-backed storage.  Nova must be able to interact with libvirt to
enable this functionality.

Data model impact
-----------------

None

REST API impact
---------------

This work is used by the os-assisted-volume-snapshots extension APIs with no
API-level changes.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

End-user impact is that Cinder volume snapshots now work when Nova
is configured to use libgfapi for the GlusterFS Cinder driver.
(qemu_allowed_storage_drivers=['gluster'])

Performance Impact
------------------

Deleting (merging) a GlusterFS volume snapshot may be more efficient,
particularly for simultaneous snapshot deletes for different volumes, as
this work uses qemu direct storage access (via libgfapi) rather than a
FUSE-mounted file system.

No direct performance impact within Nova itself.

Other deployer impact
---------------------

This change is relevant when using the Cinder GlusterFS driver and Nova
is configured with qemu_allowed_storage_drivers=['gluster'].

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  eharney

Work Items
----------

* Support for creating a volume snapshot of a network-backed disk
* Support for deleting a volume snapshot of a network-backed disk
  - Parse backing chain information from libvirt's domain XML
  - Pass new-style arguments to blockCommit and blockRebase

Dependencies
============

* This functionality depends on libvirt changes which are currently targeted
  for libvirt 1.2.6.
  - The libvirt capability is detected without using the libvirt version.

* The libvirt changes also require fixes within qemu (targeting 2.1).

* Currently only relevant for GlusterFS Cinder deployments.


Testing
=======

This should be tested via Tempest volume snapshot test cases.  Since it is
dependent on having a GlusterFS deployment this is not currently tested in
the gate.

When third-party CI is enabled for the GlusterFS driver within Cinder, it
should cover this.


Documentation Impact
====================

None


References
==========

* Required libvirt changes:
  - https://www.redhat.com/archives/libvir-list/2014-June/msg00492.html

* Required QEMU changes:
  - https://lists.gnu.org/archive/html/qemu-devel/2014-06/msg04058.html

* Based on work done in
  - https://blueprints.launchpad.net/nova/+spec/qemu-assisted-snapshots

* Patch series: https://review.openstack.org/#/c/78748/
