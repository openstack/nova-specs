..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================================
Quiescing filesystems with QEMU guest agent during image snapshotting
=====================================================================

https://blueprints.launchpad.net/nova/+spec/quiesced-image-snapshots-with-qemu-guest-agent

When QEMU Guest Agent is installed in a kvm instance, we can request the
instance to freeze filesystems via libvirt during snapshotting to make the
snapshot consistent.

Problem description
===================

Currently we need to quiesce filesystems (fsfreeze) manually before
snapshotting an image of active instances to create consistent backups.
This should be automated when QEMU Guest Agent is enabled.

(Quiescing on cinder's create-snapshot API is covered by another proposal [1]_)

Use Cases
---------

With this feature, users can create a snapshot image with consistent
file systems state while the instances are running (fsck will not run when
the snapshot image is booted).

It will be nice when:

* taking a quick backup before installing or upgrading softwares.
* automatically taking backup images every night.

Project Priority
----------------

None

Proposed change
===============

When QEMU Guest Agent is enabled in an instance, Nova-compute libvirt driver
will request the agent to freeze the filesystems (and applications if
fsfreeze-hook is installed) before taking snapshot of the image.

For boot-from-volume instances, Nova will call Cinder's snapshot-create API
for every volume attached after quiescing an instance. To avoid double
quiescing, Nova should tell Cinder not to quiesce the instance on snapshot.
For this purpose, 'quiesce=True|False' parameter will be added to
Cinder's snapshot-create API.

After taking snapshots, the driver will request the agent to thaw the
filesystems.

The prerequisites of this feature are:

1. the hypervisor is 'qemu' or 'kvm'

2. libvirt >= 1.2.5 (which has fsFreeze/fsThaw API) is installed in the
   hypervisor

3. 'hw_qemu_guest_agent=yes' property and 'hw_require_fsfreeze=yes' property
   is set on the image metadata,
   and QEMU Guest Agent is installed and enabled in the instance

When quiesce is failed even though these conditions are satisfied
(e.g. the agent is not responding), snapshotting may fail by exception
not to get inconsistent snapshots.

Alternatives
------------

Rewrite nova's snapshotting with libvirt's domain.createSnapshot API with
VIR_DOMAIN_SNAPSHOT_CREATE_QUIESCE flag, although it will change the current
naming scheme of disk images. In addition, it cannot be leveraged to implement
live snapshot of cinder volumes.

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

While taking snapshots, disk writes from the instance are blocked.

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
  tsekiyama

Work Items
----------

1. Implement the automatic quiesce during snapshotting when it is available.
2. Add a quiesced snapshotting scenario test with libvirt >= 1.2.5
   (Fedora experimental queue will be a good place to start testing.)

Dependencies
============

None

Testing
=======

Live snapshotting with an image with qemu-guest-agent should be added to
tempest.
Note that it requires environment with libvirt >= 1.2.5, so it would be
Fedora experimental queue job with virt-preview repository enabled.

Documentation Impact
====================

Need to document how to use this feature in the operation guide (which
currently recommends you use the fsfreeze tool manually).

References
==========

.. [1] Quiesce admin action for consistent snapshot:
       https://review.openstack.org/#/c/128112/
