..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
Resource Providers - Compute Node Inventory
===========================================

https://blueprints.launchpad.net/nova/+spec/compute-node-inventory-newton

As we move towards a system for generic tracking of all quantitative resources
in the system using the resource providers modeling system, we need to
transition the object model and database schema for a compute node to store
inventory information in the resource provider `inventories` table instead of
the `compute_nodes` table.  This spec outlines the part of this transition
process that deals with capacity of resources on a compute node -- the
inventory records.

Problem description
===================

Long-term, we would like to be able to add new types of resources (see the
`resource-classes` blueprint) to the system and do so without requiring
invasive database schema changes. In order to move to this more generic
modeling of quantitative resources and capacity records (see
`resource-providers` blueprint) we must transition the storage of inventory
information from where that information currently resides to the new
`inventories` table in the resource providers modeling system.

Use Cases
---------

As a deployer, I wish to add new classes of resources to my system and do so
without any downtime caused by database schema migrations.

Proposed change
===============

The two major components of this spec are the alignment of the underlying
database schema and the changes needed to the `nova.objects.ComputeNode` object
model to read and write inventory/capacity information from the `inventories`
table instead of the `compute_nodes` table.

Alignment of database schema
----------------------------

To align the underlying database storage for inventory records, we propose to
move the resource usage and capacity fields from their current locations in the
database to the new `inventories` table added in the `resource-providers`
blueprint.

Currently, the Nova database stores inventory records for the following
resource classes:

* vCPUs:

 * `compute_nodes.vcpus`: Total physical CPU cores on the compute node
 * `compute_nodes.vcpus_used`: Number of vCPUs allocated to virtual machines
   running on that compute node
 * `compute_nodes.cpu_allocation_ratio`: Overcommit ratio for vCPU on the
   compute node

* RAM:

 * `compute_nodes.memory_mb`: Total amount of physical RAM in MB on the
   compute node
 * `compute_nodes.memory_mb_used`: Amount of RAM allocated to virtual machines
   running on that compute node
 * `compute_nodes.ram_allocation_ratio`: Overcommit ratio for memory on the
   compute node
 * `compute_nodes.free_ram_mb`: A calculated field that can go away since its
   value can be determined by looking at used versus capacity values

* Disk:

 * `compute_nodes.local_gb`: Amount of disk storage available to the compute
   node for storage virtual machine ephemeral disks. While this is denoted
   "local" disk storage, currently if the local storage for ephemeral disks is
   shared storage, the compute node has no idea that this storage is shared
   among other compute nodes. See the `generic-resource-pools` and
   `resource-providers` blueprints for the solution to this problem
 * `compute_nodes.local_gb_used`: Amount of disk storage allocated for
   ephemeral disks of virtual machines running on the compute node. The same
   problem with shared storage for ephemeral disks applies to this field as
   well
 * `compute_nodes.free_disk_gb`: A calculated field that can go away since its
   value can be determined by looking at used versus capacity values
 * `disk_available_least`: A field that stores the sum of *actual* used disk
   amounts on the local compute node. This information can be stored in the new
   `max_unit` field of the `inventories` table for the `DISK_GB` resource class

* PCI devices:

 * `pci_stats`: Stores summary information about device "pools" (per
   product_id and vendor_id combination). This information is made redundant
   by the `pci-generate-stats` blueprint, which generates a summary view of
   pool information for PCI devices from the main record table, `pci_devices`
   table
 * `pci_devices` table stores all the individual PCI device records, including
   the status of the device and which instance (if any) the device has been
   assigned to.

* NUMA topologies:

 * `compute_nodes.numa_topology`: Serialized `nova.objects.numa.NUMATopology`
   object that represents both the compute node's NUMA topology **and the
   assigned NUMA topologies for instances on the compute node**.

To recap from the `resource-providers` blueprint, the schema of the
`inventories` table in the database looks like this::

    CREATE TABLE inventories (
        id INT UNSIGNED NOT NULL AUTOINCREMENT PRIMARY KEY,
        resource_provider_id INT UNSIGNED NOT NULL,
        resource_class_id INT UNSIGNED NOT NULL,
        total INT UNSIGNED NOT NULL,
        min_unit INT UNSIGNED NOT NULL,
        max_unit INT UNSIGNED NOT NULL,
        step_size INT UNSIGNED NOT NULL,
        allocation_ratio FLOAT NOT NULL,
        INDEX (resource_provider_id),
        INDEX (resource_class_id)
    );

We propose to consolidate all of the inventory/capacity fields from the above
locations into the new `inventories` table in the following manner:

Remember that all compute nodes are resource providers, but not all resource
providers are compute nodes. There is no globally-unique identifier for a
compute node within the OpenStack deployment, and we need a globally-unique
identifier for the resource provider.

1) (COMPLETED IN MITAKA) We must first add a new `uuid` field to the
`compute_nodes` table::

    ALTER TABLE compute_nodes ADD COLUMN uuid VARCHAR(36) NULL;

.. note::

    The `uuid` field must be NULL at first, since we will not be generating
    values in a schema migration script. See below for where we generate UUIDs for
    each compute node on-demand as each compute node without a UUID specified is
    read from the database.

Because we do not want to do any data migrations in SQL migration scripts, we
need to do the following data migrations in the `nova.objects.ComputeNode`
object. We propose having a method called `_migrate_inventory()` that handles
the data migration steps that is called on `_from_db_object()` when certain
conditions are found to be in place (for instance, the compute node doesn't
have a UUID field value). The `_migrate_inventory()` method should use a single
database transaction to ensure all DB writes are done atomically and it should
first check to ensure that all API and conductor nodes have been upgraded to a
version that can support the migration.

2) (COMPLETED IN MITAKA) Compute nodes that have no `uuid` field set should
have a new random UUID generated on-demand.

3) A record must be added to the `resource_providers` table for each compute
node::

    INSERT INTO resource_providers (uuid)
    SELECT uuid FROM compute_nodes;

4) We need to create the inventory records for each compute node. For each of
the resource classes that the compute node provides, we need to store the
capacity, min and max unit values, and allocation ratios.

4a) For the vCPU resource class, we would do the following steps for each
compute node. Grab the resource class identifier for CPU from the
`resource_classes` table (see `resource-classes` blueprint).

Insert into the `inventories` table a record for the CPU resource class
with the total, min, max, and allocation ratio. For example::

    INSERT INTO inventories (
        resource_provider_id,
        resource_class_id,
        total,
        min_unit,
        max_unit,
        allocation_ratio
    )
    SELECT
        rp.id,
        $CPU_RESOURCE_CLASS_ID,
        cn.vcpus,
        1,
        cn.vcpus,
        cn.cpu_allocation_ratio
    FROM compute_nodes AS cn
        JOIN resource_providers rp
           ON cn.uuid = rp.uuid
    WHERE cn.id = $COMPUTE_NODE_ID;

4b) Do the same for the RAM and DISK resource classes. For the DISK resource
class, do not perform the INSERT if the compute node uses shared storage
for the ephemeral disks.

4c) For the PCI device resource classes (`PCI_GENERIC`, `PCI_SRIOV_PF` and
`PCI_SRIOV_VF`), the inventories table records represent the class of
resources as a whole, not, for example, individual VFs on an SR-IOV-enabled
NIC PF. As such, a single record representing the total amount of each PCI
resource class would be added to the inventories table for each compute
node that has PCI devices.

For example, let us assume that a compute node has one SR-IOV-enabled NIC,
supporting 255 virtual functions (VFs) and not exposing the physical
function (PF) for use by a cloud user. We want to limit the number of VFs
that any single instance can consume to 8.

We would insert the following into the inventories table::

    INSERT INTO inventories (
        resource_provider_id,
        resource_class_id,
        total,
        min_unit,
        max_unit,
        allocation_ratio
    )
    SELECT
        rp.id,
        $PCI_SRIOV_VF_RESOURCE_CLASS_ID,
        255,
        1,
        8,
        1.0
    FROM compute_nodes AS cn
        JOIN resource_providers rp
           ON cn.uuid = rp.uuid
    WHERE cn.id = $COMPUTE_NODE_ID;

4d) For the NUMA resource classes (`NUMA_SOCKETS`, `NUMA_CORES`, `NUMA_THREADS`
and `NUMA_MEMORY`), create an inventory record for each compute node that
exposes NUMA topology resources.

For example, let us assume we have a compute node that exposes 2 NUMA nodes
(cells), each with 4 cores and 8 threads. We would set the min_unit and
max_unit values of the inventory records to the single-NUMA-cell
constraints and the total value to the combined number of the resource. So,
for instance, for the `NUMA_CORES`, we'd set total to 8 (2 sockets having 4
cores each), min_unit to 1, and max_unit to 4 (since each cell has 4 cores).

.. note::

    In the following release from when this code merges, we will do a followup
    patch that makes the UUID column non-nullable and adds a unique constraint
    on the compute_nodes.uuid column.

Changes to `ComputeNode` object model
-------------------------------------

In order to ease the transition from the old-style mechanism for determining
inventory/capacity information, we propose modifying the
`nova.objects.ComputeNode` object in following ways:

1) Make the existing `vcpus`, `memory_mb`, `local_gb`, `cpu_allocation_ratio`,
and `ram_allocation_ratio`, `disk_allocation_ratio` fields be read using a
single query against the `inventories` table and populate the values of the
object fields so that the user is none the wiser that the storage mechanism has
changed behind the scenes. A single SQL query may be used to grab the above
fields::

    SELECT
        i.resource_class_id,
        i.total,
        i.min_unit,
        i.max_unit,
        i.allocation_ratio
    FROM inventories i
      JOIN resource_providers rp
      ON i.resource_provider_id = rp.id
    WHERE rp.uuid = $COMPUTE_NODE_UUID;

2) The only piece of code that *writes* changes to the `vcpus`, `memory_mb`,
`local_gb`, `cpu_allocation_ratio`, and `ram_allocation_ratio` fields of the
`ComputeNode` is in the resource tracker, which sets the field values and calls
`save()` on the `ComputeNode` object. We can modify the `save()` method to
write any changes to inventory/capacity information to the new `inventories`
table instead of the `compute_nodes` table.

.. note::

    The object should be changed to only save capacity information to the
    inventory table, but **only** if all conductor and API nodes have been
    upgraded to a version that supports the new inventory schema.

Alternatives
------------

This is step 3 in an irreversible process that completely changes the way that
quantitative things are tracked and claimed in Nova.

Data model impact
-----------------

No other database schema changes will be required by this blueprint. The work
in this blueprint only populates the `inventories` table that is created in the
`resource-providers` blueprint.

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

There will be a database schema migration needed that adds the `uuid` column to
the `compute_nodes` table.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jaypipes

Other contributors:
  cdent
  dansmith

Work Items
----------

The following distinct tasks are involved in this spec's implementation:

* Create the database schema migration that adds the `uuid` column to the
  `compute_nodes` table
* Modify `nova.objects.ComputeNode.create()` to populate the `uuid` attribute
  of the compute node, insert a record into the `resource_providers` table and
  add any inventory/capacity fields to the `inventories` table.
* Add a `nova.objects.ComputeNode._migrate_inventory()` method to migrate the
  inventory/capacity fields from `compute_nodes` to `inventories` and populate
  `uuid` column value if it is None, as it would be if an older `nova-compute`
  daemon sent a serialized `ComputeNode` object model to an updated conductor.
  The `_migrate_inventory()` method should also create a record in the
  `resource_providers` table for the compute node
* Modify `nova.objects.ComputeNode` model to read inventory/capacity
  information from the `inventories` table instead of the `compute_nodes` table
* Modify `nova.objects.ComputeNode` model to store **changed** inventory
  information (total amount, min and max unit constraints, and allocation
  ratio) to the `inventories` table instead of the `compute_nodes` table, and
  read the inventory information from the `inventories` table instead of the
  `compute_nodes` table

Dependencies
============

* `resource-classes` blueprint implemented
* `resource-providers` blueprint implemented

Testing
=======

Full unit, functional, and integration testing of the
`ComputeNode._migrate_inventory()` method that performs the data migration
itself.

Documentation Impact
====================

Developer reference documentation only. No user-facing impact is expected from
this spec's implementation.

References
==========

* `resource-classes` blueprint: http://git.openstack.org/cgit/openstack/nova-specs/tree/specs/mitaka/approved/resource-classes.rst
* `resource-providers` blueprint: http://git.openstack.org/cgit/openstack/nova-specs/tree/specs/mitaka/approved/resource-providers.rst

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
