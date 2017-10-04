..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
List/show all server migration types
====================================

https://blueprints.launchpad.net/nova/+spec/list-show-all-server-migration-types

The following APIs are used to list in-progress server live migrations
and show an in-progress live migration's details.
So this blueprint enables us to list and show other migration types
('evacuation', 'resize', 'migration').

* GET /servers/{server_id}/migrations
* GET /servers/{server_id}/migrations/{migration_id}

Problem description
===================

To abort cold migrations [1]_, administrators have to list/show in-progress
cold migrations. But currently they can list/show in-progress live migrations
only in server migrations APIs.

Use Cases
---------

Operators want to list all in-progress migrations in the cloud [1]_.

Proposed change
===============

Modify the following existing 2 APIs for live-migration to list and show
other migration types ('evacuation', 'resize', 'migration').

* GET /servers/{server_id}/migrations
* GET /servers/{server_id}/migrations/{migration_id}

The former API returns in-progress migrations.
The latter API returns 404 error if the specified migration is not in progress.
The behavior is retained as it is.

Migration status transitions are as follows:

* Migration/resize

  - 'pre-migrating' --> 'migrating' --> 'post-migrating' --> 'finished'

* Confirm resize

  - 'finished' --> 'confirming' --> 'confirmed'

* Revert resize

  - 'finished' --> 'reverting' --> 'reverted'

* Evacuation

  - 'accepted' --> 'pre-migrating' --> 'done'

* Live migration

  - (Skip the definition)

In-progress migration states are defined as follows:

* migration/resize

  - 'pre-migrating', 'migrating', 'post-migrating'

* confirm resize

  - 'confirming'

* revert resize

  - 'reverting'

* evacuation

  - 'accepted', 'pre-migrating'

* live-migration

  - 'queued', 'preparing', 'running', 'post-migrating'
  - Existing definition. They remains as it is.

These in-progress migrations are listed/shown, but the migration status will
not be returned in the response.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

Following changes will be introduced in a new API microversion.

* GET /servers/{server_id}/migrations

  It lists in-progress migrations.
  The migration type can be specified as a 'type' query parameter
  to filter out results.
  The 'type' query parameter is optional.
  If 'type' parameter is not specified, all migration types are listed.

  The valid 'type' parameters are 'live-migration', 'migration',
  'resize' and 'evacuation'.
  If 'type' parameter is wrong, nova-api returns 400 error.
  So add badRequest(400) to error response codes.

  The 'type' parameter is added in the response.
  The migration status is not included in the response.

  JSON response body example::

    {
        "migrations": [
            {
                "dest_host": "10.0.2.15",
                "memory_processed_bytes": null,
                "type": "migration",
                "updated_at": "2017-01-31T08:03:25.000000",
                "created_at": "2017-01-31T08:03:21.000000",
                "memory_remaining_bytes": null,
                "dest_compute": "devstack-master2",
                "id": 11,
                "source_node": "devstack-master1",
                "server_uuid": "a333ee8a-367f-4841-bdc9-c8d92a6adfe4",
                "memory_total_bytes": null,
                "dest_node": "devstack-master2",
                "disk_total_bytes": null,
                "disk_processed_bytes": null,
                "disk_remaining_bytes": null,
                "source_compute": "devstack-master1"
            }
        ]
    }

* GET /servers/{server_id}/migrations/{migration_id}

  The response codes are not modified.
  Show a migration which has any migration type.
  The 'type' parameter is added in the response.
  The migration status is not included in the response.

  JSON response body example::

    {
        "migration": {
            "dest_host": "10.0.2.15",
            "memory_processed_bytes": null,
            "type": "migration",
            "updated_at": "2017-01-31T08:03:25.000000",
            "created_at": "2017-01-31T08:03:21.000000",
            "memory_remaining_bytes": null,
            "dest_compute": "devstack-master2",
            "id": 11,
            "source_node": "devstack-master1",
            "server_uuid": "a333ee8a-367f-4841-bdc9-c8d92a6adfe4",
            "memory_total_bytes": null,
            "dest_node": "devstack-master2",
            "disk_total_bytes": null,
            "disk_processed_bytes": null,
            "disk_remaining_bytes": null,
            "source_compute": "devstack-master1"
        }
    }

  If a migration is not in-progress state, it returns 404 error.

* POST /servers/{server_id}/migrations/{migration_id}/action

  It is a "Force Migration Complete Action" API.
  The migration is not a 'live-migration', it returns 400 error
  instead of 404 error.

* DELETE /servers/{server_id}/migrations/{migration_id}

  If the migration is not a 'live-migration', it returns 400 error.
  It is a current behavior. (It is not changed.)

Security impact
---------------

Only Administrator can operate suggested functions by default.
So there is no security impact.

Notifications impact
--------------------

None

Other end user impact
---------------------

The novaclient and openstackclient are modified to specify a migration type.

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
  natsume-takashi

Other contributors:
  None

Work Items
----------

* Add the 'type' query parameter to list server migrations
  ('evacuation', 'resize', 'migration') API
* Modify show a server migration ('evacuation', 'resize', or 'migration') API
* Add the optional 'type' parameter in novaclient/openstackclient
* API docs including note of the possible types

Dependencies
============

None

Testing
=======

Add the following tests.

* functional tests
* tempest test

Documentation Impact
====================

* API Reference
* CLI Reference

References
==========

.. [1] https://blueprints.launchpad.net/nova/+spec/abort-cold-migration

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Approved
   * - Queens
     - Reproposed
