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

* Extend migrations resource to get migrations statistics in a new
  microversion. Then user can get the progress details of live-migration.

  * GET `GET /servers/{id}/migrations`

  * JSON schema definition for new fields::

      non_negative_integer_with_null = {
        'type': ['integer', 'null'],
        'minimum': 0
      }

      {
        'type': 'object',
        'properties': {
          'migrations': {
            'type': 'array',
            'items': {
              'type': 'object',
              'properties': {
                'memory_total': non_negative_integer_with_null,
                'memory_remaining': non_negative_integer_with_null,
                'disk_total': non_negative_integer_with_null,
                'disk_processed': non_negative_integer_with_null,
                'disk_remainning': non_negative_integer_with_null,
                 ..{all existing fields}...
              }
              'additionalProperties': False,
              'required': ['memory_total', 'memory_remaining', 'disk_total',
                           'disk_processed', 'disk_remainning',
                           ..{all existing fields}...]
            }
          }
        },
        'additionalProperties': False,
        'required': ['migrations']
      }

  * The example of response body::

      {
        "migrations": [
          {
            "created_at": "2012-10-29T13:42:02.000000",
            "dest_compute": "compute2",
            "id": 1234,
            "server_uuid": "6ff1c9bf-09f7-4ce3-a56f-fb46745f3770",
            "new_flavor_id": 2,
            "old_flavor_id": 1,
            "source_compute": "compute1",
            "status": "running",
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


The old top-level resource `/os-migrations` won't be extended anymore, any
new features will be go to the `/servers/{id}/migrations`. The old top-level
resource `/os-migrations` just keeps for admin query, may replaced by
`/servers/{id}/migrations` totally in the future. So we should add
link in the old top-level resource `/os-migrations` for guiding people to
get the new details of migration resource.

* Proposes adding new method to get each migration resource

  * GET /servers/{id}/migrations/{id}

  * Normal http response code: 200

  * Expected error http response code

    * 404: the specific in-progress  migration can not found.

  * JSON schema definition for the response body::

      {
        'type': object,
        'properties': {
            ...{all existing fields}...
        }
        'additionalProperties': False,
        'required': [...{all existing fields}...]
      }

   * The example of response body::

       {
        "created_at": "2012-10-29T13:42:02.000000",
        "dest_compute": "compute2",
        "id": 1234,
        "server_uuid": "6ff1c9bf-09f7-4ce3-a56f-fb46745f3770",
        "new_flavor_id": 2,
        "old_flavor_id": 1,
        "source_compute": "compute1",
        "status": "running",
        "updated_at": "2012-10-29T13:42:02.000000",
        "memory_total": 1057024,
        "memory_processed": 3720,
        "memory_remaining": 1053304,
        "disk_total": 20971520,
        "disk_processed": 20880384,
        "disk_remaining": 91136,
       }

   * There is new policy will be added
     'os_compute_api:servers:migrations:show', and the default permission is
     admin only.

* Proposes adding ref link to the `/servers/{id}/migrations/{id}` for
  `/os-migrations`

  * GET /os-migrations

  * JSON schema definition for the response body::

      {
        'type': 'object',
        'properties': {
            'migrations': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                       'links': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'href': {
                                        'type': 'string',
                                        'format': 'uri'
                                    },
                                    'rel': {
                                        'type': 'string',
                                        'enum': ['self', 'bookmark'],
                                    }
                                }
                                'additionalProperties': False,
                                'required': ['href', 'ref']
                            }
                        },
                        ...
                    },
                    'additionalProperties': False,
                    'required': ['links', ...]
                }
            }
        },
        'additionalProperties': False,
        'required': ['migrations']
      }

  * The example of response body::

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
              "status": "done",
              "updated_at": "2012-10-29T13:42:02.000000",
              "links": [
                  {
                    'href': "http://openstack.example.com/v2.1/openstack/servers/0e44cc9c-e052-415d-afbf-469b0d384170/migrations/1234",
                    'ref': 'self'
                },
                {
                    'href': "http://openstack.example.com/openstack/servers/0e44cc9c-e052-415d-afbf-469b0d384170/migrations/1234"
                    'ref': 'bookmark'
                }
              ]
          },
          {
              "created_at": "2013-10-22T13:42:02.000000",
              "dest_compute": "compute20",
              "dest_host": "5.6.7.8",
              "dest_node": "node20",
              "id": 5678,
              "instance_uuid": "instance_id_456",
              "new_instance_type_id": 6,
              "old_instance_type_id": 5,
              "source_compute": "compute10",
              "source_node": "node10",
              "status": "done",
              "updated_at": "2013-10-22T13:42:02.000000"
              "links": [
                {
                    'href': "http://openstack.example.com/v2.1/openstack/servers/0e44cc9c-e052-415d-afbf-469b0d384170/migrations/5678",
                    'ref': 'self'
                },
                {
                    'href': "http://openstack.example.com/openstack/servers/0e44cc9c-e052-415d-afbf-469b0d384170/migrations/5678"
                    'ref': 'bookmark'
                }
              ]
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

New python-novaclient command will be available, e.g.

nova server-migration-list <instance>
nova server-migration-show <instance> <migration_id>

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
* Implement new commands 'server-migration-list' and 'server-migration-show' to
  python-novaclient.

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
