..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Support Cinder Volume Multi-attach
==================================

https://blueprints.launchpad.net/nova/+spec/multi-attach-volume

Currently, Nova only allows a volume to be attached to a single
instance.  There are times when a user may want to be able
to attach the same volume to multiple instances.

Problem description
===================

Currently Nova is not prepared to attach a single Cinder volume to
multiple VM instances even if the volume itself allows that operation.
This document describes the required changes in Nova to introduce this new
functionality and also lists the limitations it has.

Use Cases
---------

Allow users to share volumes between multiple guests using read-write
attachments like clustered applications with two nodes where one is active and
one is passive. Both require access to the same volume although only one
accesses actively. When the active one goes down, the passive one can take
over quickly and has access to the data.

The above example works with active/active scenario as well, it's the user's
responsibility to choose the right filesystem.


Proposed change
===============

The new 'multi-attach' functionality will be enabled by using the new Cinder
attach/detach API which is available from the API microversion 3.44 [#]_.

Cinder will only allow a volume to be attached more than once if its
'multiattach' flag is set on the volume at create time. Nova is expected to
rely on Cinder to do the check on the volume state when it's reserving the
volume on the API level by calling attachment_create.

There are problems today when multiple volume attachments share a single
target to the volume backend. If we do not take care, multi-attach would
make these problems much worse. The simplest fix is to serialize all attach and
detach operations involving a shared target. To do this Cinder will expose
a volume info property of 'shared_targets', when True a lock will be
placed around all attachment_update and attachment_delete calls, and the
associated calls to os-brick.::

 # The lock uses the volume.backend_uuid value.
 with optional_host_local_lock(acquire=volume.shared_target):
   connector = os_brick.get_connector()
   conn_info = attachment.update(connector).conn_info
   os_brick.connect_volume(conn_info)
   attachment.attach_complete()

 with optional_host_local_lock(acquire=volume.shared_target):
   os_brick.disconnect_volume(conn_info)
   attachment.delete()

.. note::

  We assume the detach and attach related calls to Cinder are synchronous so
  there will be no races between os-brick operations on the host and cinder
  operations on the backend. Any driver deviation from this pattern will be
  considered a bug.

By default libvirt assumes all disks are exclusively used by a single guest.
If you want to share disks between instances, you need to tell libvirt
when configuring the guest XML for that disk via setting the 'shareable' flag
for the disk. This means that the hypervisor will not try to take an exclusive
lock on the disk, that all I/O caching is disabled, and any SELinux labeling
allows use by all domains.

Nova needs to set this 'shareable' flag for the multi-attach volumes (where the
'multattach' flag is set to True) for every single attachment. This spec will
only enable this feature for libvirt, all other drivers should reject attach
calls to multi-attach volumes, until that driver adds support to this
functionality. The information is stored among the virt driver capabilities
dict in the base ComputeDriver where support multi-attach will be True for
Libvirt and for all other virt drivers this capability is disabled. To
introduce the usage of the flag we will also need to bump the minimum compute
version.

The following policy rules will be added to Cinder:

* Enable/Disable multiattach=True
* Enable/Disable multiattach=True + bootable=True

Nova should reject the attach request in case the hypervisor does not support
it, but with the current API it is not possible. This can be solved in part
with the policy rules above. For example, if you're running a cloud with
computes that don't support multiattach, let's say it's all vmware, then the
operator can configure policy to disable multiattach volumes on the cinder
side. If you've got a mixed hypervisor cloud and the user tries to attach a
multiattach volume to an instance on a compute where the virt driver doesn't
support multiattach, then the attach request fails on the compute and
nova-compute calls attachment_delete to delete the attachment created in
nova-api's attach_volume code. If nova-api exposed backend compute driver
capabilities then we could check and fail fast in the API, but nova doesn't
have that yet so we're just left with policy rules and checks on the backend.

Alternatives
------------

For the use case described above the failover scenario can be handled by
attaching the volume to the passive/standby instance. This means that the
standby instance is not a hot standby anymore as the volume attachment
requires time, which means that the new primary instance is without volume
for the time of re-attaching, which can vary in the sense of marking the
volume free after the failure of the primary instance.

Another alternative is to clone a volume and attach the clone to the second
instance. The downside to this is any changes to the original volume don't
show up in the mounted clone so this is only a viable alternative if the
volume is read-only.

Data model impact
-----------------

None

REST API impact
---------------

There are features of the Nova API that has to be handled by care or disabled
completely for now for volumes that support multi-attach.

The create call in the 'os-assisted-volume-snapshot' API calls the
'volume_snapshot_create' where we don't have the instance_uuid to retrieve the
right BDM, therefore we need to disable this call for multi-attach. The API
format for this request is not changed, it is only a protection until the
required API changes to support this request with multi-attach.

Another feature that needs further investigation is 'boot from volume' (BFV).
The first aspect of the feature is the 'delete_on_termination' flag, which will
be allowed to use along with multi-attach, no changes are necessary when the
volume provided has multiattach=True and the delete_on_termination=True flag is
passed in for BFV. When this flag is set to True it is intended to remove the
volume that is attached to the instance when it is deleted. This option does
not cause problem as Cinder takes care of not deleting a volume if it still
has active attachments. Nova will receive an error from Cinder that the volume
deletion failed, which will then be logged [#]_ and also in the API on
'_local_delete' [#]_, but will not affect the instance termination process.

The second aspect of BFV is the boot process. In this case Nova only checks the
'bootable' flag. The policy check happens on the Cinder side on allowing it
together with multiattach or not.

For cases, where Nova creates the volume itself, i.e. source_type is
blank/image/snapshot, it should not enable multi-attach for the volume, i.e. no
change to the existing code for now.

When we attach a volume at boot time (BFV with source=volume,dest=volume)
scheduling will fail in case of selecting computes that do not support
multi-attach. Later on we can add a new scheduler filter to avoid the failure.
The filter would check the compute capabilities. This step is considered
to be a future improvement.

When we enable the feature we will have a 'multiattach' policy to enable or
disable the operation entirely on the Cinder side as noted above. Read/Only
policy is a future work item and out of the scope of this spec.

A new compute API microversion will be added since users will need
some way to discover if they can perform volume multiattach. The semantics
of the microversion will be similar to the `2.49`_ microversion for tagged
attach.

.. _2.49: https://docs.openstack.org/nova/latest/reference/api-microversion-history.html#id44

Security impact
---------------

In the libvirt driver, the disk is given a shared SELinux label,
and so that disk has no longer strong sVirt SELinux isolation.

The OpenStack volume encryption capability is supposed to work out of the
box with this use case also, it should not break how the encryptor works
below the clustered file system, by using the same key for all connections.
The attachment of an encrypted volume to multiple instances should be
tested in Tempest to see if there is any unexpected issue with it.

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

Based on the work from Walter Boring and Charlie Zhou.
Agreed with Walter to start the work again.

Assignee(s)
-----------

Primary assignee:
    ildiko-vancsa


Work Items
----------

1. Update libvirt driver to generate proper domain XML for instances with
   multi-attach volumes
2. Provide the necessary checks in the Nova API to block the operation in the
   above listed cases
3. Add Tempest test cases and documentation

Dependencies
============

* This requires the version 3.2.0 or above of the python-cinderclient.
  Corresponding blueprint:
  https://blueprints.launchpad.net/python-cinderclient/+spec/multi-attach-volume

* Corresponding, implemented spec in Cinder:
  https://blueprints.launchpad.net/cinder/+spec/multi-attach-volume

* Link needed to Cinder spec to address detach issues currently captured here:
  https://etherpad.openstack.org/p/cinder-nova-api-changes

Testing
=======

We'll have to add new Tempest tests to support the new Cinder volume
multiattach flag. The new cinder multiattach flag is what allows a volume to be
attached more than once. For instance the following scenarios will need to be
tested:

* Attach the same volume to two instances.
* Boot from volume with multiattach
* Encrypted volume with multiattach
* Boot from multi-attachable volume with boot_index=0
* Negative testing:

 * Tying to attach a non-multiattach volume to multiple instances

Additionally to the above, Cinder migrate needs to be tested on the gate, as it
triggres swap_volume in Nova.

Documentation Impact
====================

We will have to update the documentations to discuss the new ability to
attach a volume to multiple instances if the cinder multiattach flag is set
on a volume. It is also need to be added to the documentation that the volume
creation for these types of volumes will not be supported by the API due to
the deprecation of the volume creation Nova API. If a volume needs to allow
multiple volume attachments it has to be created on the Cinder side with
the needed properties specified.

It also needs to be outlined in the documentation that attaching a volume
multiple times in read-write mode can cause data corruption, if not handled
correctly. It is the users' responsibility to add some type of exclusion
(at the file system or network file system layer) to prevent multiple writers
from corrupting the data. Examples should be provided if available to guide
users on how to do this.


References
==========

* This is the cinder wiki page that discusses the approach to multi-attach
  https://wiki.openstack.org/wiki/Cinder/blueprints/multi-attach-volume

* Queens PTG etherpad:
  https://etherpad.openstack.org/p/cinder-ptg-queens-thursday-notes

.. [#] https://docs.openstack.org/cinder/latest/contributor/api_microversion_history.html#id41

.. [#] http://lists.openstack.org/pipermail/openstack-dev/2016-May/094089.html

.. [#] https://github.com/openstack/nova/blob/295224c41e7da07c5ddbdafc72ac5abf2d708c69/nova/compute/manager.py#L2369

.. [#] https://github.com/openstack/nova/blob/295224c41e7da07c5ddbdafc72ac5abf2d708c69/nova/compute/api.py#L1834

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Kilo
     - Introduced
   * - Liberty
     - Re-approved
   * - Mitaka-1
     - Re-approved
   * - Mitaka-2
     - Updated with API limitations and testing scenarios
   * - Newton
     - Re-approved
   * - Queens
     - Re-proposed
