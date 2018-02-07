..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
RBD Instance Snapshots
======================

https://blueprints.launchpad.net/nova/+spec/rbd-instance-snapshots

When using RBD as storage for glance and nova, instance snapshots are
slow and inefficient, resulting in poor end user experience. Using
local disk for the upload increases operator costs for supporting
instance snapshots.

As background reading the follow link provides an overview of the
snapshotting capabilities available in ceph.

http://docs.ceph.com/docs/master/rbd/rbd-snapshot/

Problem description
===================

RBD is often used to back glance images and nova disks. When using rbd
for nova's disks, nova 'snapshots' are slow, since they create full
copies by downloading data from rbd to a local file, uploading it to
glance, and putting it back into rbd. Since raw images are normally
used with rbd to enable copy-on-write clones, this process removes any
sparseness in the data uploaded to glance. This is a problem of user
experience, since this slow, inefficient process takes much longer
than necessary to let users customize images.

For operators, this is also a problem of efficiency and cost. For
rbd-backed nova deployments, this is the last part that uses
significant local disk space.

Use Cases
----------

This allows end users to quickly iterate on images, for example to
customize or update them, and start using the snapshots far more
quickly.

For operators, this eliminates any need for large local disks on
compute nodes, since instance data in rbd stays in rbd. It also
prevents lots of wasted space.

Project Priority
-----------------

None

Proposed change
===============

Instead of copying all the data to local disk, keep it in RBD by
taking an RBD snapshot in Nova and cloning it into Glance.  Rather
than uploading the data, just tell Glance about its location in
RBD. This way data stays in the Ceph cluster, and the snapshot is
far more rapidly usable by the end user.

In broad strokes, the workflow is as follows:

  1. Create an RBD snapshot of the ephemeral disk via Nova in
     the ceph pool Nova is configured to use.

  2. Clone the RBD snapshot into Glance's RBD pool. [7]

  3. To keep from having to manage dependencies between snapshots
     and clones, deep-flatten the RBD clone in Glance's RBD pool and
     detach it from the Nova RBD snapshot in ceph. [7]

  5. Remove the RBD snapshot from ceph created in (1) as it is no
     longer needed.

  6. Update Glance with the location of the RBD clone created and
     flattend in (2) and (3).

This is the reverse of how images are cloned into nova instance disks
when both are on rbd [0].

If any of these steps fail, clean up any partial state and fall back
to the current full copy method. Failure of the RBD snapshot method
will be quick and usually transient in nature. The cloud admin can
monitor for these failures and address the underlying CEPH issues
causing the RBD snapshot to fail.

Failures will be reported in the form of stack traces in the nova
compute logs.

There are a few reasons for falling back to full copies instead of
bailing out if efficient snapshots fail:

  * It makes upgrades graceful, since nova snapshots still work
    before glance has enough permissions for efficient snapshots
    (see Security Impact for glance permission details).

  * Nova snapshots still work when efficient snapshots are not
    possible due to architecture choices, such as not using rbd as
    a glance backend, or using different ceph clusters for glance
    and nova.

  * This is consistent with existing rbd behavior in nova and cinder.
    If cloning from a glance image fails, both projects fall back
    to full copies when creating volumes or instance disks.

Alternatives
------------

The clone flatten step could be handled as a background task in a
green thread, or completely asynchronously as a periodic task.  This
would increase user-facing performance, as the snapshots would be
available for use immediately, but it would also introduce
race-condition-like issues around deleting dependent images.

The flatten step could be omitted completely, and glance could be
made responsible for tracking the various image dependencies.  At
the rbd level, an instance snapshot would consist of three things
for each disk. This is true of any instance, regardless of whether
it was created from a snapshot itself, or is just created from a
usual image. In rbd, there would be:

  1. a snapshot of the instance disk

  2. a clone of the instance disk

  3. a snapshot of the clone

  (3) is exposed through glance's backend location.
  (2) is an internal detail of glance.
  (1) is an internal detail that nova and glance handle.

At the rbd level, a disk with snapshots can't be deleted. Hide this
from the user if they delete an instance with snapshots by making
glance responsible for their eventual deletion, once their dependent
snapshots are deleted. Nova does this by renaming instance disks that
it deletes in rbd, so glance is aware that they can be deleted.

When a glance snapshot is deleted, it deletes (3), then (2), and
(1). If nova has renamed its parent in rbd with a preset suffix, the
instance has been destroyed already, so glance tries to delete the
original instance disk. The original instance disk will be
successfully deleted when the last snapshot is removed.

If glance snapshots are created but deleted before the instance is
destroyed, nova will delete the instance disks as usual.

The mechanism nova uses to let glance know it needs to clean up the
original disk could be different. It could use an image property with
certain restrictions which aren't possible in the current glance api:

  * it must be writeable only once

  * to avoid exposing backend details, it would need to be hidden
    from end users

Storing this state in ceph is much easier to keep consistent with
ceph, rather than an external database which could become out of sync.
It would also be an odd abstraction leak in the glance_store api, when
upper layers don't need to be aware of it at all.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

Glance will need to be configured with direct_url support enabled
in order for Nova to determine what and where to clone the image
from, depending on system configurations, this could leak backend
credentials [5].  Devstack has already been updated to switch
behaviors when Ceph support is requested [6].

Documentation has typically recommended using different ceph pools
for glance and nova, with different access to each. Since nova
would need to be able to create the snapshot in the pool used by
glance, it would need write access to this pool as well.

Notifications impact
--------------------

None

Performance Impact
------------------

Snapshots of RBD-backed instances would be significantly faster.

Other end user impact
---------------------

Snapshots of RBD-backed instances would be significantly faster.

Other deployer impact
---------------------

To use this in an existing installation with authx, adding 'allow
rwx pool=images' to nova's ceph user capabilities is necessary. The
'ceph auth caps' command can be used for this [1]. If these permissions
are not updated, nova will continue using the existing full copy
mechanism for instance snapshots because the fast snapshot will fail
and nova compute will fall back to the full copy method.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  nic

Other contributors:
  jdurgin
  pbrady
  nagyz
  cfb-n/cburgess

Work Items
----------

Implementation: [4]

The libvirt imagebackend does not currently recognize AMI images
as raw (and therefore cloneable) for whatever reason, so this
proposed change is of limited utility with a very popular image
format.  This should be addressed in a separate change.

Dependencies
============

You need a Havana or newer version of glance as direct URL was added in
Havana.

Testing
=======

The existing tempest tests with ceph in the gate cover instance
snapshots generically. As fast snapshots are enabled automatically, there
is no need to change the tempest tests. Additionally, unit tests in nova
will verify error handling (falling back to full copies if the process
fails), and make sure that when configured correctly rbd snapshots and
clones are used rather than full copies.

Documentation Impact
====================

See the security and other deployer impact sections above.

References
==========

[0] http://specs.openstack.org/openstack/nova-specs/specs/juno/implemented/rbd-clone-image-handler.html

[1] Ceph authentication docs: http://ceph.com/docs/master/rados/operations/user-management/#modify-user-capabilities

[2] Alternative: Glance cleanup patch: https://review.openstack.org/127397

[3] Alternative: Nova patch: https://review.openstack.org/125963

[4] Nova patch: https://review.openstack.org/205282

[5] https://bugs.launchpad.net/glance/+bug/880910

[6] https://review.openstack.org/206039

[7] http://docs.ceph.com/docs/master/dev/rbd-layering/
