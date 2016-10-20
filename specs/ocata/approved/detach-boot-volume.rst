..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
Detach and attach boot volumes
==============================

https://blueprints.launchpad.net/nova/+spec/detach-boot-volume

It is sometimes useful for a cloud user to be able to detach and attach
the boot volume of an instance when the instance is not running. Currently
nova does not allow this at all and some operations assume it does not happen.
This spec proposes allowing the detach and attach of boot volumes when an
instance is shelved and adding safeguards to ensure it is safe.

Problem description
===================

There is an implicit assumption in the nova code that an instance always has
a cinder boot volume attached or an ephemeral boot disk. Nova allows cinder
volumes to be detached and attached at any time, but the detach operation is
limited to exclude boot volumes to preserve the above assumption.

This limitation means it is not possible to change the boot volume
attached to an instance except by deleting the instance and creating a new
one. However, it is safe to change boot volume attachments when an instance
is not running, so preventing this altogether is unnecessarily limiting.

There are use cases that require a boot volume to be detached when an
instance is not running, so we propose relaxing the inherent assumption to
say that a boot volume attachment can be changed when an instance is shelved.
To ensure safety we can prevent it being unshelved without a boot volume.

Use Cases
---------

The first use case is based on a disaster recovery scenario. In this
scenario a system of VMs attached to a network and using persistent
volumes at site A is executing an online application. To provide a
remote failure recovery capability the data on the persistent volumes is
being replicated to volumes at remote site B. The persistent volumes
include boot volumes.

The use case is the following:

  As a cloud user I want to be able to failover my application to a remote
  site with minimal down time and the assurance that the remote site is
  able to take over.

The ability to detach and attach boot volumes is required for this use case
as implemented by the following failover from site A to site B:

1. Build the virtual infrastructure in advance at site B and check that
   the new infrastructure is complete, correctly configured and operable.
   Then shelve the instances and detach the disks. This infrastructure is
   now ready to take over when supplied with replica disks.

2. Set up continuous replication of disks from site A to site B

3. The failover procedure: stop replication to site B; attach replica
   disks to the shelved instances; unshelve the instances.

The outline above shows that the virtual infrastructure at site B is built
in advance and is kept in a dormant state. The volumes are detached and
kept up to date as replicas of the volumes at site A, to be swapped back
in later. This satisfies the requirements of the use case:

  Firstly, the build of the infrastructure, including instances that will
  receive replica volumes, can be done and checked to be correct before
  performing the failover. This gives a higher level of assurance that the
  switchover will be successful.

  Secondly, by removing the virtual infrastructure build from the critical
  path of the failover (steps 3-7), the down time caused by the failover
  is minimised.

A bug registered against nova describes further use cases (see [1]). An
example is the following:

  As a user I want to run a VM with a windows instance. I will take snapshots
  of the boot volume from time to time. I may want to revert to a snapshot.
  If I delete my instance and recreate it from the snapshot I will incur
  additional costs from licensing and may invalidate my license.

Proposed change
===============

This change assumes that only cinder volumes can be dynamically changed
in this way. We will not support detaching ephemeral disks.

Volume backed instances are always offloaded when shelved, so the instance
will not be on a host. As a result the implementation will be to change
the recorded block device mapping and register the attachment/detachment
with cinder.

The usual detach volume API call will be used to detach the boot volume.
The guard on this call will be changed to allow the detach if the instance
is shelved_offloaded.

When a boot volume is detached its block device mapping will be replaced
with a block device mapping that indicates there is no volume. A new
boolean field called device_present will be added for this purpose;
device_present = False means the device is missing and cannot be used.

The usual attach volume API call will be used to attach the boot volume.
The volume attach operation allows a user to specify the name of the device.
The boot device name of an instance is known so that is used to determine
that the user is attempting to attach the volume as the root device. The
attachment will only be allowed if the instance is shelved_offloaded and
it has a "no volume" block device mapping for the root device.

The unshelve operation will be guarded with a check for the "no volume"
block device mapping. An instance will not be allowed to unshelve when
its boot volume has been detached unless another has been attached in its
place.

There is a race condition identified in this bug [2] between volume
operations and instance state changes. The same race condition will
exist between the boot volume detach and the unshelve operations until
that bug is fixed. That bug will be addressed by spec [3].

Alternatives
------------

One alternative is simply not to allow a boot volume to be detached. This
implies that root devices can only be changed by deleting and recreating
an instance. Currently many devices on an instance can be added and removed
dynamically.

We could generalize further and allow a boot volume to be detached and
attached when an instance is shutdown as well. This would involve affecting
the connection to the hypervisor on the compute node. The ability to do this
for boot volumes is inherent in the existing volume device code, so it seems
unnecessary to disable it. However, this throws open many more corner cases
in the code and is not needed for the above use cases.

Another alternative is to be more general by allowing any type of boot
device to be removed and any type added. This would include images on local
ephemeral disks, snapshots and volumes. Because this goes beyond the
existing volume API this generalization would suggest
the need for a new API. This is not needed to satisfy the use cases
provided so we propose restricting this behavior to the existing APIs.

Another alternative is to only allow boot volumes to be swapped in a single
operation. This retains the assumption that an instance always has a volume
(except during the operation) but removes some flexibility. In the disaster
recovery use case an instance could be shelved and its boot volume detached.
If the instance must have a volume at all times this will require a second
volume (besides the replica) for each instance that is not being used. This
is wasteful of resources.

Data model impact
-----------------

A boolean field called device_present will be added to the BlockDeviceMapping
object and to the block_device_mapping database table. The default value
for this field will be True.

Setting the device_present field to False will indicate that the block
device mapping is a place holder for a missing device and cannot be used.

REST API impact
---------------

There will be no change to the operations or parameters of the REST API.

An attempt to detach a boot volume currently always returns the error:

  "Can't detach root device volume (HTTP: 403)"

This will change in the case of an instance being in the shelved_offloaded
state to allow the detach.

An attempt to unshelve an instance that has a missing boot volume
because it has been detached will return an error:

  "Can't unshelve instance without a root device volume (HTTP: 403)"

These error changes will require an API micro version increment.

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

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  paul.carlton2@hpe.com

Other contributors:
  pmurray@hpe.com

Work Items
----------

This spec will build on the ground work of [4].
The following changes are part of this spec.

- Add device_present field to BlockDeviceMapping object and
  block_device_mapping database table.

- Add "no volume" block device mapping utility methods to indicate a boot
  device has been removed. These will create the "no volume" block device
  mapping setting the device_present field and inspect the mapping for
  a volume that is not present.

- Extend methods to attach/detach volumes for shevled_offloaded instances
  to deal with boot volume and "no volume" block device mapping.

- Add guard in API for "no volume" mapping before unshelving an instance.

- Change conditional guard on compute api to allow detach of boot device
  when instance is shelved_offloaded.

Dependencies
============

This spec extends the volume operations enabled by [4].

There is a parallel (but not dependant) spec [3] that addresses bug [2].
That spec is not required for this one, but it is worth noting that this
feature will benefit from the general bug fix dealt with there.

Testing
=======

All the existing volume operations have both unit tests and system tests.
The changes described here can be covered in nova by unit tests.

We will also add system tests to tempest after the changes are made to
ensure coverage of the new use cases for the detach and attach operations.

Documentation Impact
====================

Document when a root device volume can be detached and attached.

Error return when trying to start an instance with no root device.

References
==========

[1] Add capability to detach root device volume of an instance, when in
    shutoff state. https://bugs.launchpad.net/nova/+bug/1396965

[2] Volume operations should set task state.
    https://bugs.launchpad.net/nova/+bug/1275144

[3] https://blueprints.launchpad.net/nova/+spec/avoid-parallel-conflicting-api-operations

[4] https://blueprints.launchpad.net/nova/+spec/volume-ops-when-shelved


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
   * - Newton
     - Re-proposed.
   * - Ocata
     - Re-proposed.
