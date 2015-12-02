..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Report more live migration progress detail
==========================================

Blueprint:
https://blueprints.launchpad.net/nova/+spec/live-migration-progress-report

When live migrations take a long time, an operator might want to take some
actions on it, such as pause the VM being migrated or cancel the live
migrations operation, or do some performance optimization.
All these actions will need based on the judgment of migration progress detail.

This spec proposes adding more progress detail report for live migration
in os-migrations API.

Problem description
===================

Some busy enterprise workloads hosted on large sized VM, such as SAP ERP
Systems, VMs running memory write intensive workloads, this may lead migration
not converge.

Now nova can not report more details of migration statistics, such as how many
data are transferred, how many data are remaining.
Without those details, the operator may not decide how to take the next action
on the migration.

Use Cases
----------

* As an operator of an OpenStack cloud, I would like to know the detail of the
  migration, then I can pause/cancel or do some performance optimization.

* Some other projects, such as watcher project, want to make a strategy to
  optimize performance dynamically during live migration. The strategy depends
  on some details status of migration.

Proposed change
===============

Extend os-migrations API. Some new fields will be added in migration DB
and os-migrations API response.

The new fields will be updated to the migration object in
live_migration_monitor method of the libvirt driver so that API call just
needs to retrieve the object form db, traditionally API calls do not block
while they send a request to the compute node and wait for a reply.

New fields:
 * memory_total:  the total guest memory size.
 * memory_processed: the amount memory has been transferred.
 * memory_remaining: amount memory remaining to transfer.
 * disk_total: total disk size.
 * disk_processed: amount disk has been transferred.
 * disk_remaining: amount disk remaining to transfer.

Note, the migration is always unbounded job, memoryTotal may be less than the
final sum of memoryProcessed + memoryRemaining in the event that the hypervisor
has to repeat some memory, such as due to dirtied pages during migration.

The same is true of the disk numbers. And Disk fields will all be zero when not
block migrating.

For cold migration, only the disk fields will be populated, for the drivers
that doesn't expose migration detail, the memory and disk fields will be null.

Alternatives
------------

Add a new API to report the migration status details.

Data model impact
-----------------

The `nova.objects.migration.Migration` object would have 6 new fields.

For the database schema, the following table constructs would suffice ::

    CREATE TABLE migrations(
        `created_at` datetime DEFAULT NULL,
        `updated_at` datetime DEFAULT NULL,
        `deleted_at` datetime DEFAULT NULL,
        `id` int(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
        `source_compute` varchar(255) DEFAULT NULL,
        `dest_compute` varchar(255) DEFAULT NULL,
        `dest_host` varchar(255) DEFAULT NULL,
        `status` varchar(255) DEFAULT NULL,
        `instance_uuid` varchar(36) DEFAULT NULL,
        `old_instance_type_id` int(11) DEFAULT NULL,
        `new_instance_type_id` int(11) DEFAULT NULL,
        `source_node` varchar(255) DEFAULT NULL,
        `dest_node` varchar(255) DEFAULT NULL,
        `deleted` int(11) DEFAULT NULL,
        `migration_type` enum('migration','resize','live-migration',
            'evacuation') DEFAULT NULL,
        `hidden` tinyint(1) DEFAULT NULL,
        `memory_total` bigint DEFAULT NULL,
        `memory_processed` bigint DEFAULT NULL,
        `memory_remaining` bigint DEFAULT NULL,
        `disk_total` bigint DEFAULT NULL,
        `disk_processed` bigint DEFAULT NULL,
        `disk_remaining` bigint DEFAULT NULL,
        index(`instance_uuid`),
        index(`deleted`)
    );


REST API impact
---------------

Extend os-migrations to get migrations statistics in a new microversion.
Response Body::

  {
    "migrations": [
      {
        "created_at": "2012-10-29T13:42:02.000000",
        "dest_compute": "compute2",
        "dest_host": "1.2.3.4",
        "dest_node": "node2",
        "id": 1234,
        "instance_uuid": "instance_id_123",
        "new_instance_type_id": 2,
        "old_instance_type_id": 1,
        "source_compute": "compute1",
        "source_node": "node1",
        "status": "Done",
        "updated_at": "2012-10-29T13:42:02.000000",
        "memory_total": 1057024,
        "memory_processed": 3720,
        "memory_remaining": 1053304,
        "disk_total": 20971520,
        "disk_processed": 20880384,
        "disk_remaining": 91136,
      },
    ]
  }


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

User can easily get the live migration progress.

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

Assignee(s)
-----------

Primary assignee:
  ShaoHe Feng <shaohe.feng@intel.com>

Other contributors:
  Yuntong Jin <yuntong.jin@intel.com>

Work Items
----------
* Add migration progress detail fields in DB.
* Write migration progress detail fields to DB.
* update the migration object in _live_migration_monitor method of the libvirt
  driver.
* The API call to list os-migrations simply return data about the migration
  objects, i.e. what is in DB.

Dependencies
============

None


Testing
=======

Unittest and funtional tests in Nova

Documentation Impact
====================

Doc the API change in the API Reference:
http://developer.openstack.org/api-ref-compute-v2.1.html

References
==========

os-migrations-v2.1:
http://developer.openstack.org/api-ref-compute-v2.1.html#os-migrations-v2.1

History
=======

Mitaka: Introduced
