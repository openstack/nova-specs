..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================================
Add pagination and changes-since filter support for os-migrations API
=====================================================================

https://blueprints.launchpad.net/nova/+spec/
add-pagination-and-change-since-for-migration-list

This blueprint add `limit` and `marker` optional
parameters to GET /os-migrations request to support pagination.

This blueprint also add `changes-since` optional parameters to
GET /os-migrations request to support filtering response data by updated time.

Problem description
===================

Currently, os-migrations API does not support pagination. As in large
scale deployment the number of migration records can be also very large
query them all can lead to performance bottleneck, it will be very
useful to support pagination.

Also, os-migrations API does not support filter the migration record by
last updated time. As for production deployment, the system will be up
for a very long time, and the number of migration records will also be
very big. It will be very useful to support filter by last update time.

Use Cases
---------

For large scale production deployment, the administrator can use
pagination and lastest updated time filter to have more efficient
database query.

Proposed change
===============

Add an API microversion that allows to get several migrations using
general pagination mechanism with the help of `limit` and `marker`optional
parameters to GET /os-migrations request. And add
filter with the help of `changes-since` optional parameter to
GET /os-migrations request.

* **marker**: The last migration ID of the previous page. Displays list of
  migrations after "marker".

* **limit**: Maximum number of migrations to display. If limit == -1,
  all migrations will be displayed. If limit is bigger than `osapi_max_limit`
  option of Nova API, limit `osapi_max_limit` will be used instead.


Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

The proposal would add API microversion for getting several migrations using
general pagination mechanism. New optional parameters `limit`, `marker`,
and `changes-since` will be added to GET /os-migrations request.

Generic request format ::

    GET /os-migrations?limit={limit}&marker={migration_id}

1) Get all migrations ::

    GET /os-migrations

   Response ::

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
            "updated_at": "2012-10-29T13:42:02.000000"
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
            "status": "Done",
            "updated_at": "2013-10-22T13:42:02.000000"
        },
        {
            "created_at": "2013-10-22T13:45:02.000000",
            "dest_compute": "compute21",
            "dest_host": "5.6.7.8",
            "dest_node": "node21",
            "id": 5679,
            "instance_uuid": "instance_id_4561",
            "new_instance_type_id": 6,
            "old_instance_type_id": 5,
            "source_compute": "compute10",
            "source_node": "node10",
            "status": "Done",
            "updated_at": "2013-10-22T13:45:02.000000"
        }
    ]
    }

2) Get no more than 2 migrations ::

    GET /os-migrations?limit=2

   Response ::

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
            "updated_at": "2012-10-29T13:42:02.000000"
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
            "status": "Done",
            "updated_at": "2013-10-22T13:42:02.000000"
        }
    ]
    }

3) Get all migrations after id=1234 ::

    GET /os-migrations?marker=1234

   Response ::

    {
    "migrations": [
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
            "status": "Done",
            "updated_at": "2013-10-22T13:42:02.000000"
        },
        {
            "created_at": "2013-10-22T13:45:02.000000",
            "dest_compute": "compute21",
            "dest_host": "5.6.7.8",
            "dest_node": "node21",
            "id": 5679,
            "instance_uuid": "instance_id_4561",
            "new_instance_type_id": 6,
            "old_instance_type_id": 5,
            "source_compute": "compute10",
            "source_node": "node10",
            "status": "Done",
            "updated_at": "2013-10-22T13:45:02.000000"
        }
    ]
    }



Request format ::

    GET /os-migrations?changes-since=2013-10-22T13:45:02.000000

Response ::

    {
    "migrations":[
        {
            "created_at": "2013-10-22T13:45:02.000000",
            "dest_compute": "compute21",
            "dest_host": "5.6.7.8",
            "dest_node": "node21",
            "id": 1234,
            "instance_uuid": "instance_id_4561",
            "new_instance_type_id": 6,
            "old_instance_type_id": 5,
            "source_compute": "compute10",
            "source_node": "node10",
            "status": "Done",
            "updated_at": "2013-10-22T13:45:02.000000"
        }
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

None

Performance Impact
------------------

Reduce load on Horizon with the help of pagination and time filtering
of retrieving migrations from Nova side.

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
  Zheng Zhenyu

Work Items
----------

Create a new API microversion for getting several migrations using general
pagination mechanism and time stamp filtering.

Dependencies
============

None

Testing
=======

Would need new Tempest, functional and unit tests.

Documentation Impact
====================

Docs needed for new API microversion and usage.

References
==========
