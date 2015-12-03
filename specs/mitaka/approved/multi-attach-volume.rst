..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Support Cinder Volume Multi-attach
==================================

https://blueprints.launchpad.net/nova/+spec/multi-attach-volume

Currently, Nova only allows a volume to be attached to a single
host or instance.  There are times when a user may want to be able
to attach the same volume to multiple instances.

Problem description
===================

Currently, Nova only allows a volume to be attached to one instance
and or host at a time. Nova makes an assumption in a number of places
that assumes the limitation of a single volume to a single instance
regardless of the fact that Cinder now supports attaching and detaching
a volume to/from multiple instances. Nova assumes that if a volume is
attached, it can't be attached again, see nova/volume/cinder.py:
check_attach() for details.

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

At attach time, Nova has to remove the assumption that it can only attach
a volume if it's not 'in-use'. A Cinder volume can now be attached if it's
'available' and/or 'in-use'. Cinder will only allow a volume to be attached
more than once if it's 'multiattach' flag is set on the volume at create time.

At detach time, Nova needs to pass the attachment_id to the cinderclient
to tell cinder which specific attachment it's requesting to detach. Since
a volume can be attached to an instance and/or a host, we cannot skip to
pass the attachment_uuid at detach time.  Passing only an instance uuid
is insufficient as cinder provides the possibility to attach a volume to
a host. If it isn't passed in and there are multiple attachments, then
cinder will fail because it won't know which attachment to detach. On
Nova side the attachment_id can be identified by getting the volume
attachments from the volume_api and search for the attachment by using the
instance_uuid, it does not have to be stored in Nova.

By default libvirt assumes all disks are exclusively used for a single guest.
If you want to share disks between instances, you need to tell libvirt
when configuring the guest XML for that disk via setting the sharable flag
for the disk. This means that the hypervisor will not try to take an exclusive
lock on the disk, that all I/O caching is disabled, and any SELinux labeling
allows use by all domains.

Nova needs to set this sharable flag for the multi-attach disks of the
instances.


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

API impacts are described in a follow up spec.


Security impact
---------------

In the libvirt driver, the disk is given a shared SELinux label,
and so that disk has no longer strong sVirt SELinux isolation.

The OpenStack volume encryption capability is supposed to work out of the
box with this use case also, it should not break how the encryptor works
below the clustered file system, by using the same key for all connections.
The issues, if there will be any will be handled on the run.

Notifications impact
--------------------

None

Other end user impact
---------------------

The command line will now allow you to call Nova volume-attach for a volume
to multiple instances.

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

1. Update the use of cinderclient to extract the new list of volume
   attachments when Nova fetches a volume.
2. Update all calls to cinderclient.detach() to include the attachment uuid.
3. Update libvirt driver to generate proper domain XML for instances with
   multi-attach volumes

Dependencies
============

* This requires the version 1.3.1 or above of the python-cinderclient.
  Corresponding blueprint:
  https://blueprints.launchpad.net/python-cinderclient/+spec/multi-attach-volume

* Corresponding, implemented spec in Cinder:
  https://blueprints.launchpad.net/cinder/+spec/multi-attach-volume


Testing
=======

We'll have to add new Tempest tests to support the new Cinder volume sharable
flag. The new cinder sharable flag is what allows a volume to be attached
more than once or not. Have to look into a tempest test for attaching the
same volume to multiple instances.


Documentation Impact
====================

We will have to update the documentations to discuss the new ability to
attach a volume to multiple instances if the cinder sharable flag is set on a
volume. It is also need to be added to the documentation that the volume
creation for these types of volumes will not be supported by Nova due to
the deprecation of the volume creation API. If a volume needs to allow
multiple volume attachments it has to be created on the Cinder side with
the needed properties specified.

It also needs to be outlined in the documentation that attaching a volume
multiple times in read-write mode can cause data corruption, if not handled
correctly. It is the users' responsibility to add some type of exclusion
(at the file system or network file system layer) to prevent multiple writers
from corrupting the data.


References
==========

* This is the cinder wiki page that discusses the approach to multi-attach
  https://wiki.openstack.org/wiki/Cinder/blueprints/multi-attach-volume
