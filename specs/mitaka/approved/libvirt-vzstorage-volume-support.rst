..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================================
Libvirt: Support for attaching volumes located on Virtuozzo Storage
===================================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-vzstorage-volume-support

Currently, there are Libvirt volume drivers that support network-attached
file systems such as Gluster, NFS or SMB. The purpose of this blueprint is
to add ability to attach volumes hosted by Virtuozzo Storage.

Problem description
===================

Virtuozzo Storage is a fault-tolerant distributed storage system, optimized
for virtualization workloads. From client's point of view it looks like network
attached storage (NFS or GlusterFS).

Virtuozzo Storage allows to use disk space of conventional linux systems to
provide fault-tolerant storage with automatic recovery. It's optimized for
performance of virtualization workloads and has strong data consistency.

Use Cases
----------

Deployer will be able to attach block storage exported in the form of virtual
disks on Virtuozzo Storage to instances.

Proposed change
===============

A new volume driver will be added in order to support attaching volumes
located on Virtuozzo Storage. The volume driver will have a similar workflow
as NFS and SMBFS volume drivers have.

The CI system will be running on Nova tree and checking each Nova patch with
Virtozzo Storage. The CI aims to eventually vote on every relevant Nova
patchset

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

The share credentials will be parsed in the volume connection info and used
when mounting a Virtuozzo Storage cluster.

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

The deployer will be able to configure the path where the Virtuoozo Storage
clusters  will be mounted, as well as setting mount flags.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <dguryanov@virtuozzo.com>

Work Items
----------

Add support for mounting Virtuozzo Storage clusters.

Dependencies
============

None


Testing
=======

This feature should be tested using the Virtuozzo Storage Cinder Volume
driver. The existing Tempest tests along with the according unit tests
should be enough for the moment in order to test this.

While a CI is being considered, for the moment Tempest tests will be run
periodically for this scenario.

Documentation Impact
====================

Using the Virtuozzo Storage backend will be documented.

References
==========

Cinder Virtuozzo Storage Driver blueprint:
https://blueprints.launchpad.net/cinder/+spec/virtuozzo-cloud-storage-support


