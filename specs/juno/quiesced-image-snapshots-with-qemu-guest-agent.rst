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

Proposed change
===============

When QEMU Guest Agent is enabled in an instance, Nova-compute libvirt driver
will request the agent to freeze the filesystems (and applications if
fsfreeze-hook is installed) before taking snapshot of the image.
After taking snapshot, the driver will request the agent to thaw the
filesystems.

The prerequisites of this feature are:

1. the hypervisor is 'qemu' or 'kvm'

2. libvirt >= 1.2.5 (which has fsFreeze/fsThaw API) is installed in the
   hypervisor

3. 'hw_qemu_guest_agent=yes' property in the image metadata is set to 'yes'
   and QEMU Guest Agent is installed and enabled in the instance

When quiesce is failed even though these conditions are satisfied
(e.g. the agent is not responding), snapshotting may fail by exception
not to get inconsistent snapshots.

Alternatives
------------

Rewrite nova's snapshotting with libvirt's domain.reateSnapshot API with
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

Implement the automatic quiesce during snapshotting when it is available.
Now the code is ready to  review: https://review.openstack.org/#/c/72038/

Dependencies
============

None

Testing
=======

Live snapshotting with an image with qemu-guest-agent should be added to
scenario tests.
Note that it requires environment with libvirt >= 1.2.5.

Documentation Impact
====================

Need to document how to use this feature in the operation guide (which
currently recommends you use the fsfreze tool manually).

References
==========

None
