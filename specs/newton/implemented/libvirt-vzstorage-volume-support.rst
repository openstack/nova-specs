..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================================
Libvirt: Support for attaching volumes located on Virtuozzo Storage
===================================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-vzstorage-volume-support

The purpose of this blueprint is to add an ability to use volumes hosted by
Virtuozzo Storage [1]_ previously implemented as one of Cinder Drivers [2]_.

Problem description
===================

Virtuozzo Storage is a fault-tolerant distributed storage system. From
client's point of view it is a remote file system storage similar to
NFS, GlusterFS or CIFS.

Virtuozzo Storage allows to use disk space of conventional linux systems to
provide fault-tolerant storage with automatic recovery. It's optimized for
performance of virtualization workloads and has strong data consistency.

Use Cases
----------

A user is able to attach block storage exported in the form of virtual
disks resided on Virtuozzo Storage to Nova instances.

Proposed change
===============

A new volume driver is added in order to support attaching volumes resided on
Virtuozzo Storage. This volume driver has a similar workflow to what NFS
and SMBFS volume drivers have.

The CI system [3]_ runs on Nova tree and checks each Nova patch with
Virtozzo Storage and leaves a comment about status of tempest run.

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
  eantyshev

Other contributors:
  mnestratov, dguryanov


Work Items
----------

Spec approval.
Implementation: [4]_
Documentaiton.

Dependencies
============

Remotefs os-brick part merged in review [5]_
Cinder part implementation merged in review [6]_


Testing
=======

This feature should be tested in conjunction with the Virtuozzo Storage
Cinder Volume driver. The existing Tempest tests along with the related unit
tests should be enough.

A third party CI testing system is up and running [3]_

Documentation Impact
====================

Using the Virtuozzo Storage backend should be documented.

References
==========
.. [1] https://virtuozzo.com/wp-content/uploads/2016/03/Virtuozzo_Virtuozzo_Storage_DS_A4_EN_20160305.pdf
.. [2] https://blueprints.launchpad.net/cinder/+spec/virtuozzo-cloud-storage-support
.. [3] https://wiki.openstack.org/wiki/ThirdPartySystems/Virtuozzo_Storage_CI
.. [4] https://review.openstack.org/#/c/190843/
.. [5] https://review.openstack.org/#/c/188805/
.. [6] https://review.openstack.org/#/c/188869/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Approved.
   * - Newton
     - Re-introduced.
