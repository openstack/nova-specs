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

Allow users to share volumes between multiple guests using either
read-write or read-only attachments. Clustered applications
with two nodes where one is active and one is passive. Both
require access to the same volume although only one accesses
actively. When the active one goes down, the passive one can take
over quickly and has access to the data.



Proposed change
===============

The changes needed in Nova are related to attach time and detach time.

Cinder will only allow a volume to be attached more than once if its
'multiattach' flag is set on the volume at create time. Nova is expected to
rely on Cinder to do the check on the volume state during 'reserve_volume'
by following the changes [#]_ in the interaction of these two modules.

At detach time, Nova needs to pass the attachment_id to the cinderclient
to tell cinder which specific attachment it's requesting to detach. This change
was added during Mitaka by getting the volume info from the volume_api and
searching for the attachment by using the instance_uuid.

Beyond the aformentioned change Nova still needs to know when it can safely
disconnect the volume. Cinder is planned to provide the information to Nova,
the change will be added under new API microversion(s). Nova will not support
multi-attach, when Cinder does not have the minimum required microversion.

By default libvirt assumes all disks are exclusively used by a single guest.
If you want to share disks between instances, you need to tell libvirt
when configuring the guest XML for that disk via setting the 'shareable' flag
for the disk. This means that the hypervisor will not try to take an exclusive
lock on the disk, that all I/O caching is disabled, and any SELinux labeling
allows use by all domains.

Nova needs to set this 'shareable' flag for the multi-attach disks of the
instances. Only the libvirt driver is modified to support multi-attach, for
all other virt drivers this capability is disabled, the information is stored
among the virt driver capabilities dict in the base ComputeDriver. Nova should
reject the attach request in case the hypervisor does not support it, but
with the current API it is not possible. This could probably be solved with
policies later on but as a first we will leave it for the computes to fail in
case of not running libvirt.

Due to the need to add the 'shareable' flag to the guest xml and further
possible changes in the computes for detach we need to check whether the min
version is high enough to enable multi-attach.


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

Another feature that needs limitations is the 'boot from volume' (BFV). In case
of this feature two aspects need further investigation. The first is the
'delete_on_termination' flag, which if set to True is intended to remove the
volume that is attached to the instance when it is deleted. This option does
not cause problem as Cinder takes care of not deleting a volume if it still
has active attachments. Nova will receive an error from Cinder that the volume
deletion failed, which will then be logged [#]_, but will not affect the
instance termination process. According to this this flag will be allowed to
use along with multi-attach, no changes are necessary when the volume provided
has multiattach=True and the delete_on_termination=True flag is passed in for
BFV.

The second aspect of BFV is the boot process. In this case the only issue
comes with the bootable volumes, which are specified in the boot request as
boot device. For this the 'block_device_mapping' list has to be checked to
filter out the cases when we have a multiattachable volume specified as boot
device. It can be done by checking the 'source_type' and 'destination_type'
of a BDM and also search for 'boot_index': 0 item in the BDM dict. Based on
the volume_id stored within the BDM information the volume can be retrieved
from Cinder to check whether the 'multiattach' flag is set to True in which
case the request will return an error that this operation is not supported
for multi-attach volumes.

For cases, where Nova creates the volume itself, i.e. source_type is
blank/image/snapshot, it should not enable multi-attach for the volume for now.

When we attach a volume at boot time (BFV with source=volume,dest=volume)
scheduling will retry in case of selecting computes that do not support
multi-attach. To make it more efficient, later on we can add a new scheduler
filter to avoid the overhead of repeating the scheduling until a valid host is
found. The filter would check the compute capabilities. This step is considered
to be a future improvement.


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

Any time new code is added to Nova that requires a call to detach
a volume, the developer must get the volume attachment uuid for
the instance. This information is embedded in the cinder volume
volume_attachments list.


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

* This requires the version 1.3.1 or above of the python-cinderclient.
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
* Negative testing:

 * Boot from multi-attachable volume with boot_index=0
 * Tying to attach a non-multiattach volume to multiple instances

Additionally to the above, Cinder migrate needs to be tested on the gate, as it
triggres swap_volume in Nova that is not tested today at all.

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

.. [#] http://lists.openstack.org/pipermail/openstack-dev/2016-May/094089.html

.. [#] https://github.com/openstack/nova/blob/295224c41e7da07c5ddbdafc72ac5abf2d708c69/nova/compute/manager.py#L2369

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
