..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Resource Providers - Base Models
================================

https://blueprints.launchpad.net/nova/+spec/resource-providers

This blueprint partially addresses the problem of Nova assuming all resources
are provided by a single compute node by introducing a new concept -- a
resource provider -- that will allow Nova to accurately track and reserve
resources regardless of whether the resource is being exposed by a single
compute node, some shared resource pool or an external resource-providing
service of some sort.

Problem description
===================

Within a cloud deployment, there are a number of resources that may be consumed
by a user. Some resource types are provided by a compute node; these types of
resources include CPU, memory, PCI devices and local ephemeral disk. Other
types of resources, however, are not provided by a compute node, but instead
are provided by some external resource pool. An example of such a resource
would be a shared storage pool like that provided by Ceph or an NFS share.

Unfortunately, due to legacy reasons, Nova only thinks of resources as being
provided by a compute node. The tracking of resources assumes that it is the
compute node that provides the resource, and therefore when reporting usage of
certain resources, Nova naively calculates resource usage and availability by
simply summing amounts across all compute nodes in its database. This ends up
causing a number of problems [1] with usage and capacity amounts being
incorrect.

Use Cases
----------

As a deployer that has chosen to use a shared storage solution for storing
instance ephemeral disks, I want Nova and Horizon to report the correct
usage and capacity information.

Proposed change
===============

We propose to introduce new database tables and object models in Nova that
store information about the inventory/capacity information of generic providers
of various resources, along with a table structure that can store
usage/allocation information for that inventory.

**This blueprint intentionally does NOT insert records into these new database
tables**. The tables will be populated with the work in the follow-up
`compute-node-inventory`, `compute-node-allocations`, and
`generic-resource-pools` blueprints.

We are going to need a lookup table for the IDs of various resource
providers in the system, too. We'll call this lookup table
`resource_providers`::

    CREATE TABLE resource_providers (
        id INT UNSIGNED NOT NULL AUTOINCREMENT PRIMARY KEY,
        uuid VARCHAR (64) NOT NULL,
        UNIQUE INDEX (uuid)
    );

An `inventories` table records the amount of a particular resource that is
provided by a particular resource provider::

    CREATE TABLE inventories (
        id INT UNSIGNED NOT NULL AUTOINCREMENT PRIMARY KEY,
        resource_provider_id INT UNSIGNED NOT NULL,
        resource_class_id INT UNSIGNED NOT NULL,
        total INT UNSIGNED NOT NULL,
        reserved INT UNSIGNED NOT NULL,
        min_unit INT UNSIGNED NOT NULL,
        max_unit INT UNSIGNED NOT NULL,
        step_size INT UNSIGNED NOT NULL,
        allocation_ratio FLOAT NOT NULL,
        INDEX (resource_provider_id),
        INDEX (resource_class_id)
    );

The `reserved` field shall store the amount the resource provider "sets aside"
for unmanaged consumption of its resources. By "unmanaged", we refer here to
Nova (or the eventual broken-out scheduler) not being involved in the
allocation of some of the resources from the provider. As an example, let's say
that a compute node wants to reserve some amount of RAM for use by the host,
and therefore reduce the amount of RAM that the compute node advertises as its
capacity. As another example, imagine a shared resource pool that has some
amount of disk space consumed by things other than Nova instances. Or, further,
a Neutron routed network containing a pool of IPv4 addresses, but Nova
instances may not be assigned the first 5 IP addresses in the pool.

The `allocation_ratio` field shall store the "overcommit" ratio for a
particular class of resource that the provider is willing to tolerate. This
information is currently stored only for CPU and RAM in the
`cpu_allocation_ratio` and `ram_allocation_ratio` fields in the `compute_nodes`
table.

The `min_unit` and `max_unit` fields shall store "limits" information for the
type of resource. This information is necessary to ensure that a request for
more or fewer resource that can be provided as a single unit will not be
accepted.

.. note::

    **How min_unit, max_unit, and allocation_ratio work together**

    As an example, let us say that a particular compute node has two
    quad-core Xeon processors, providing 8 total physical cores. Even though the
    cloud administrator may have set the `cpu_allocation_ratio` to 16
    (the default), the compute node cannot accept requests for instances needing
    more than 8 vCPUs. So, while there may be 128 total vCPUs available on the
    compute node, the `min_unit` would be set to 1 and the `max_unit` would be
    set to `8` in order to prevent unacceptable matching of resources to requests.

The `step_size` is a representation of the divisible unit amount of the
resource that may be requested, *if the requested amount is greater than
the `min_unit` value*.

For instance, let's say that an operator wants to ensure that a user can only
request disk resources in 10G increments, with nothing less than 5G and nothing
more than 1TB. For the `DISK_GB` resource class, the operator would set the
inventory of the shared storage pool to a `min_unit` of 5, a `max_unit` of
1000, and a `step_size` of 10. This would allow a request for 5G of disk space
as well as 10G and 20G of disk space, but not 6, 7, or 8GB of disk space. As
another example, let's say an operator set their `VCPU` inventory record on a
particular compute node to be `min_unit` of 1, `max_unit` of 16, and
`step_size` of 2, that would mean a user can request an instance only consumes
1 vCPU, but if the user requests more than a single vCPU, that number must be
divisible evenly by 2, up to a maximum of 16.

In order to track resources that have been assigned and used by some consumer
of that resource, we need an `allocations` table. Records in this table
will indicate the amount of a particular resource that has been allocated to a
given consumer of that resource from a particular resource provider::

    CREATE TABLE allocations (
        id INT UNSIGNED NOT NULL AUTOINCREMENT PRIMARY KEY,
        resource_provider_id INT UNSIGNED NOT NULL,
        consumer_id VARCHAR(64) NOT NULL,
        resource_class_id INT UNSIGNED NOT NULL,
        used INT UNSIGNED NOT NULL,
        INDEX (resource_provider_id, resource_class_id),
        INDEX (consumer_id),
        INDEX (resource_class_id)
    );

When a consumer of a particular resource claims resources from a provider,
a record is inserted into to the `allocations` table.

.. note::

    The `consumer_id` field will be the UUID of the entity that is consuming
    this resource. This will always be the Nova instance UUID until some future
    point when the Nova scheduler may be broken out to support more than just
    compute resources. The `allocations` table is populated by logic outlined
    in the `compute-node-allocations` specification.

Alternatives
------------

Continue to use the `compute_nodes` table to store all resource usage and
capacity information. The problem with this are as follows:

* Any new resources require changes to the database schema
* We have nowhere in the database to indicate that some resource is shared
  among compute nodes

Data model impact
-----------------

A number of data model changes will be needed.

* New models for:

 * `ResourceProvider`
 * `InventoryItem`
 * `AllocationItem`

* New database tables for all of the above

* Database migrations needed:

 * Addition of following tables into the schema:

  * `resource_providers`
  * `inventories`
  * `allocations`

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
  dstepanenko

Other contributors:
  jaypipes

Work Items
----------

* Create database migration that creates the `resource_providers`,
  `inventories`, and `allocations` tables
* Create the new `nova.objects` models for `ResourceProvider`, `InventoryItem`,
  and `AllocationItem`

Dependencies
============

* The `resource-classes` blueprint work is a foundation for this work, since
  the `resource_class_id` field in the `inventories` and `allocations` table
  refers (logically, not via a foreign key constraint) to the resource class
  concept introduced in that blueprint spec.

Testing
=======

New unit tests for the migrations and new object models should suffice for this
spec.

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

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
