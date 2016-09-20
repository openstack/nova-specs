..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Resource Providers - Allocations
================================

https://blueprints.launchpad.net/nova/+spec/resource-providers-allocations

This blueprint specification explains the process of migrating the data that
stores allocated/assigned resource amounts from the older schema to the new
schema introduced in the `resource-providers` spec.

Problem description
===================

In the `compute-node-inventory-newton` work, we populate the new
resource-providers `inventories` table in the API database by having the
resource tracker simultaneously write data to both the child cell database via
the existing `ComputeNode.save()` call as well as write to the new
resource-providers `inventories` table in the API database by a new
`ResourceProvider.set_inventory()` call.

We need to similarly populate resource allocation information in the new
resource-providers `allocations` table in the API database.

Use Cases
---------

As a deployer that has chosen to use a shared storage solution for storing
instance ephemeral disks, I want Nova and Horizon to report the correct
usage and capacity information.

Proposed change
===============

We propose to have the resource tracker populate allocation information in the
API database by calling two new placement REST API methods.  `PUT
/allocations/{consumer_uuid}` will be called when an
instance claims resources on the local compute node (either a new instance or a
migrated instance).  `DELETE
/allocations/{consumer_uuid}` will be called when an
instance is terminated or migrated off of the compute node. Note that the
`generic-resource-pools` spec includes the server side changes that implement
the above placement REST API calls.

These calls to will be made **in addition to** the existing calls to
`ComputeNode.save()` and `Instance.save()` that currently save allocation and
usage information in the child cell `compute_nodes` and `instance_extra`
tables, respectively.

**NOTE**: In Newton, we plan to have the resource tracker send allocation
records to the placement API for the following resource classes: `VCPU`,
`MEMORY_MB`, `DISK_GB`, `PCI_DEVICE`. For NUMA topology classes and
`SRIOV_NET_*`, those resource classes will be handled in Ocata when the nested
resource providers work is stabilized.

Alternatives
------------

We could continue to store allocated resource amounts in the variety of field
storage formats that we currently do. However, adding new resource
classes/types will almost inevitably result in yet another field being added to
the database schema and a whole new way of accounting hacked into Nova.

Data model impact
-----------------

None.

REST API impact
---------------

None.

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

For some period of time, there will be a negative performance impact from the
resource tracker making additional calls via the placement HTTP API. The impact
of this should be minimal and not disruptive to tenants.

Other deployer impact
---------------------

The new placement REST API (implemented in the `generic-resource-pools`
blueprint) needs to be deployed for this to work, clearly. That makes the
`generic-resource-pools` a clear dependency for this.

Developer impact
----------------

None. The new placement API will of course need to be well-documented, but
there is no specific developer impact this change introduces outside of reading
up on the new placement API.

Implementation
==============

To recap from the `generic-resource-pools` spec_, there are two placement REST
API calls for creating and deleting sets of allocation (usage) records against
a resource provider:

.. _spec: http://specs.openstack.org/openstack/nova-specs/specs/newton/approved/generic-resource-pools.html


* `PUT /allocations/{consumer_uuid}`
* `DELETE /allocations/{consumer_uuid}`

The resource tracker shall call the `PUT` API call, supplying all amounts of
resources that the instance (the consumer) gets allocated on the compute node
(the resource provider). The `PUT` API call writes all of the allocation
records (one for each resource class being consumed) in a transactional manner,
ensuring no partial updates.

When an instance is terminated, the corresponding `DELETE` API call will be
made from the resource tracker, which will atomically delete all allocation
records for that instance (consumer) on the compute node (resource provider).

Calls to the `PUT` API call will also be made for existing instances during the
resource tracker's periodic `update_available_resource()` method.

Calls to the `DELETE` API call that return a `404 Not Found` will simply be
ignored on the Nova compute node.

.. note::

    The "local delete" functionality of the nova-api service can shoot an
    instance record in the cell database in the head even when connectivity to
    the nova-compute the instance is running on is down. In these cases, we
    will rely on the audit process in the resource tracker's
    `update_available_resource()` method to properly call DELETE on any
    allocations in the placement API for instances that no longer exist.

When constructing the payload for the `PUT` placement API call, the resource
tracker should examine the `Instance` object (and/or `Migration` object) for a
variety of usage information for different resource classes. The
`consumer_uuid` part of the URI should be the instance's `uuid` field value.
The `resource_provider_uuid` should be the compute node's UUID except for when
shared storage is used or boot from volume was used (see instructions below).
The payload's "allocations" field is a dict, with the keys being the string
representation of the appropriate `nova.objects.fields.ResourceClass` enum
values (e.g. "VCPU" or "MEMORY_MB").

Handle the various resource classes in the following way:

* For the `MEMORY_MB` and `VCPU` resource classes, use the
  `Instance.flavor.memory_mb` and `vcpus` field values

* For the `DISK_GB` resource class, follow these rules:

 * When the compute node utilizes **local storage for instance disks** OR was
   **booted from volume**, the value used should be the sum of the `root_gb`,
   `ephemeral_gb`, and `swap` field values of the flavor. The
   `resource_provider_uuid` should be the **compute node's UUID**. Note that
   for instances that were booted from volume, the `root_gb` value will be 0.

 * When the compute utilizes **shared storage** for instance disks and the
   instance was **NOT** booted from volume, the value used should be the sum of
   the `root_gb`, `ephemeral_gb`, and `swap` field values of the flavor. The
   `resource_provider_uuid` should eventually be the **UUID of the resource
   provider of that shared disk storage**. However, until the cloud admin
   creates a resource provider for the shared storage pool and associates that
   provider to a compute node via a host aggregate association, there is no way
   for the resource tracker to know what the UUID of that shared storage
   provider will be.

* If the `pci_devices` table contains any records linking the instance UUID to
  any PCI device in `ALLOCATED` status, create one allocation record for
  the records with dev_type of `type-PCI`. `type-PCI` dev_type indicates a
  generic PCI device. We are not yet creating allocation records for the more
  complex PCI device types corresponding to SR-IOV devices. The value of the
  record should be the total number of `type-PCI` devices. For example, if an
  instance is associated with two generic PCI devices on a compute node, the
  resource tracker should add an element to the "allocations" dict of the `PUT`
  payload that looks like this::

    "PCI_DEVICE": 2

.. note::

    We will not be creating allocation records for SR-IOV PCI devices or NUMA
    topology resources in Newton. These allocation records, along with their
    related inventory records, will be done in Ocata.

Assignee(s)
-----------

Primary assignee:
  jaypipes

Other contributors:
  cdent

Work Items
----------

The following distinct tasks are involved in this spec's implementation:

* Modify the resource tracker to create allocation records for all
  above-mentioned resource class via calls to the placement HTTP API.
* Full functional integration tests added which validates that the allocations
  table in the API database is being populated with proper data.

Dependencies
============

* `resource-classes` blueprint must be completed before this one.
* `generic-resource-pools` blueprint must be completed before this one.
* `compute-node-inventory-newton` blueprint must be completed before this one
  because it ensures each compute node is added as a resource provider with a
  UUID.

Testing
=======

Full unit and functional integration tests must be added that demonstrate the
migration of allocation-related fields is done appropriately and in a
backwards-compatible way.

Documentation Impact
====================

None.

References
==========

[1] Bugs related to resource usage reporting and calculation:

* Hypervisor summary shows incorrect total storage (Ceph)
  https://bugs.launchpad.net/nova/+bug/1387812
* rbd backend reports wrong 'local_gb_used' for compute node
  https://bugs.launchpad.net/nova/+bug/1493760
* nova hypervisor-stats shows wrong disk usage with shared storage
  https://bugs.launchpad.net/nova/+bug/1414432
* report disk consumption incorrect in nova-compute
  https://bugs.launchpad.net/nova/+bug/1315988
* VMWare: available disk spaces(hypervisor-list) only based on a single
  datastore instead of all available datastores from cluster
  https://bugs.launchpad.net/nova/+bug/1347039
