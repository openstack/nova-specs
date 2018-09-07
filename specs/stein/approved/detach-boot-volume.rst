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
instance is powered off or shelved and adding safeguards to ensure it is safe.

Problem description
===================

There is an implicit assumption in the nova code that an instance always has
a cinder boot volume attached or an ephemeral boot disk. Nova allows cinder
volumes to be detached and attached at any time, but the detach operation is
limited to exclude boot volumes to preserve the above assumption[1].

This limitation means it is not possible to change the boot volume
attached to an instance except by deleting the instance and creating a new
one. However, it is safe to change boot volume attachments when an instance
is not running, so preventing this altogether is unnecessarily limiting.

There are use cases that require a boot volume to be detached when an
instance is not running, so we propose relaxing the inherent assumption to
say that a boot volume attachment can be changed when an instance is powered
off or shelved. To ensure safety we can prevent it being started or unshelved
without a boot volume.

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
  path of the failover, the down time caused by the failover is minimised.

A bug registered against nova describes further use cases (see [2]). An
example is the following:

  As a user I want to run a VM with a windows instance. I will take snapshots
  of the boot volume from time to time. I may want to revert to a snapshot.
  If I delete my instance and recreate it from the snapshot I will incur
  additional costs from licensing and may invalidate my license.

Proposed change
===============

This change assumes that only cinder volumes can be dynamically changed
in this way. We will not support detaching ephemeral disks.

Volume backed instances are always offloaded after a period of time[3]
when shelved, so the instance will not be on a host. As a result the
implementation will be to change the recorded block device mapping and
register the attachment/detachment with cinder.

The usual detach volume API call will be used to detach the boot volume.
The guard on this call will be changed to allow the detach if the instance
is powered off or shelved_offloaded.

When a boot volume is detached, we will set the root block device
mapping(boot_index=0) with ``volume_id=None``, meaning that it's not
attached to any volume.

A new microversion will be added to the attach volume API. A new ``is_root``
parameter will be allowed for requests with the new microversion or greater,
indicating that the user is trying to attach a root volume. The attachment
with this parameter will only be allowed if the instance is powered off or
shelved_offloaded and it has a "no volume" block device mapping for the
root device.

There are some specific considerations for detaching/attaching a root volume
instances, here is what will happen:

- Detach:

   Delete the volume attachment referenced via the BDM.attachment_id field
   and null out the BDM.attachment_id and BDM.volume_id fields (save those
   changes to the DB). At that point the old root volume is made 'available'
   again. For shelved instances, this will be handled by API service. For,
   stopped instance, this will be handled by nova-compute service, thus the
   compute service version will be bumped in order to represent that detach
   root volume for deleted instance is supported.

- Attach:

   Find the root BDM via BlockDeviceMappingList.root_bdm(); at this point
   the root BDM has a null attachment_id and volume_id.

   Create a volume attachment record for the new root volume [4] and then
   update the BDM's attachment_id and volume_id fields and save those to
   the DB.

   The normal error conditions around volume attach will be in play,
   i.e. you can't attach a volume that is already in-use unless
   it's a multiattach volume.

The start and unshelve operation will be guarded with a check for the
"no volume" block device mapping. An instance will not be allowed to
start or unshelve when its boot volume has been detached unless another
has been attached in its place.

For dettach/attach volume for powered off instances, This would involve
affecting the connection to the hypervisor on the compute node, thus
will depend on the ability of compute drivers. We are now aware of that
``libvirt``, ``vmaware`` and ``xen`` driver will be capable of doing this.
The feature support matrix will be appropriately updated for this feature.

There is a race condition identified in this bug [5] between volume
operations and instance state changes. The same race condition will
exist between the boot volume detach and the unshelve operations until
that bug is fixed. That bug will be addressed by spec [6].

Alternatives
------------

One alternative is simply not to allow a boot volume to be detached. This
implies that root devices can only be changed by deleting and recreating
an instance. Currently many devices on an instance can be added and removed
dynamically.

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

None

REST API impact
---------------

Add a new microversion for attach volume REST API to allow passing
``is_root`` as a parameter.

An attempt to detach a boot volume currently always returns the error:

  "Can't detach root device volume (HTTP: 403)"

This will change in the case of an instance being in stopped or
shelved_offloaded state to allow the detach.

An attempt to start or unshelve an instance that has a missing boot volume
because it has been detached will return an error:

  "Can't unshelve instance without a root device volume (HTTP: 403)"

These error changes will also require an API micro version increment.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

The python-novaclient and python-openstackclient will be updated to
support the new capability.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

Compute service version will be bumped to represent that the
feature for detach_volume flow for deleted instance is supported.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Zhenyu Zheng


Work Items
----------

This spec will build on the ground work of [7].
The following changes are part of this spec.

- Add "no volume" block device mapping utility methods to indicate a boot
  device has been removed. These will create the "no volume" block device
  mapping setting the ``volume_id`` field to ``None`` and inspect the
  mapping for a volume that is not present.


- Extend methods to detach volumes for stopped and shelved_offloaded
  instances to deal with boot volume and "no volume" block device mapping.
  Add a new microversion to attach volume API to indicate that the specified
  volume is a root volume.

- Add guard in API for "no volume" mapping before start and unshelving an
  instance.

- Change conditional guard on compute api to allow detach of boot device
  when instance is stopped or shelved_offloaded.

Dependencies
============

This spec extends the volume operations enabled by [7].

There is a parallel (but not dependant) spec [6] that addresses bug [5].
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

Feature support matrix will be updated about this capability.

References
==========

[1] Check for root volume when doing detach
    https://github.com/openstack/nova/blob/aa9f9448c9cf77bb1e55aa0cde5e7f9c4e0157c4/nova/api/openstack/compute/volumes.py#L434

[2] Add capability to detach root device volume of an instance, when in
    shutoff state. https://bugs.launchpad.net/nova/+bug/1396965

[3] shelved_offload_time config option
    https://docs.openstack.org/nova/latest/configuration/config.html#DEFAULT.shelved_poll_interval

[4] Cinder attachment create
    https://github.com/openstack/nova/blob/85b36cd2f82ccd740057c1bee08fc722209604ab/nova/volume/cinder.py#L710

[5] Volume operations should set task state.
    https://bugs.launchpad.net/nova/+bug/1275144

[6] https://blueprints.launchpad.net/nova/+spec/avoid-parallel-conflicting-api-operations

[7] Spec for volume-ops-when-shelved (Completed in Mitaka)
    https://blueprints.launchpad.net/nova/+spec/volume-ops-when-shelved


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
   * - Stein
     - Re-proposed.