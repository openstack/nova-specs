..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================
VMware live migration
=====================

https://blueprints.launchpad.net/nova/+spec/vmware-live-migration

This is a proposal for adding support for live migration in the VMware
driver. When the VMware driver is used, each nova-compute is managing a
single vCenter cluster. For the purposes of this proposal we assume that
all nova-computes are managing clusters under the same vCenter server. If
migration across different vCenter servers is attempted, an error message
will be generated and no migration will occur.

Problem description
===================

Live migration is not supported when the VMware driver is used.

Use Cases
---------

As an Operator I want to live migrate instances from one compute cluster
(nova-compute host) to another compute cluster (nova-compute host) in the
same vCenter server.

Proposed change
===============

Relocating VMs to another cluster/datastore is a simple matter of calling the
RelocateVM_Task() vSphere API. The source compute host needs to know the
cluster name and the datastore regex of the target compute host. If the
instance is located on a datastore shared between the two clusters, it will
remain there. Otherwise we will choose a datastore that matches the
datastore_regex of the target host and migrate the instance there. There will
be a pre live-migration check that will verify that both source and
destination compute nodes correspond to clusters in the same vCenter server.

A new object will be introduced (VMwareLiveMigrateData) which will carry the
host IP, the cluster name and the datastore regex of the target compute host.
All of them are obtained from the nova config (CONF.vmware.host_ip,
CONF.vmware.cluster_name and CONF.vmware.datastore_regex).

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

None

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

Upgrade impact
--------------

None

Implementation
==============

https://review.openstack.org/#/c/270116/

Assignee(s)
-----------

Primary assignee:
  rgerganov

Work Items
----------

* Add ``VMwareLiveMigrateData`` object
* Implement pre live-migration checks
* Implement methods for selecting target ESX host and datastore
* Ensure CI coverage for live-migration
* Update support-matrix

Dependencies
============

None

Testing
=======

The VMware CI will provision two nova-computes and will execute the live
migration tests from tempest.

Documentation Impact
====================

The feature support matrix should be updated to indicate that live migration
is supported with the VMware driver.

References
==========

http://pubs.vmware.com/vsphere-60/topic/com.vmware.wssdk.apiref.doc/vim.VirtualMachine.html#relocate


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
   * - Ocata
     - Reproposed
   * - Pike
     - Reproposed
   * - Queens
     - Reproposed
   * - Rocky
     - Reproposed
   * - Stein
     - Reproposed
