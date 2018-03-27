..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================================
Add pagination and changes-since filter support for os-migrations API
=====================================================================

https://blueprints.launchpad.net/nova/+spec/add-pagination-and-change-since-for-migration-list

This blueprint adds `limit` and `marker` optional
parameters to GET /os-migrations request to support pagination.

This blueprint also adds `changes-since` optional parameter to
GET /os-migrations request to support filtering response data by last
updated time.

Problem description
===================

Currently, os-migrations API does not support pagination. As in large
scale deployment the number of migration records can be also very large
and querying them all can lead to performance bottleneck, it will be very
useful to support pagination.

Also, os-migrations API does not support filtering the migration record by
last updated time. As for production deployment, the system will be up
for a very long time, and the number of migration records will also be
very big. It will be very useful to support filter by last updated time.

Use Cases
---------

For large scale production deployment, the administrator can use
pagination and last updated time filter to have more efficient
database query.

Proposed change
===============

Add an API microversion that allows to get several migrations using
general pagination mechanism with the help of `limit` and `marker` optional
parameters to GET /os-migrations request. And add filter with the help
of `changes-since` optional parameter to GET /os-migrations request.

* **marker**: The last migration UUID of the previous page. Displays list of
  migrations after "marker".

* **limit**: Maximum number of migrations to display. If limit is bigger than
  `[api]/max_limit` option of Nova API, limit `[api]/max_limit` will be used
  instead.

For multiple cells, we could have migrations with same ID, the migration
ID as pagination marker won't work. Currently, the migration record has a
uuid column on it [1]_, we just need add the migration UUID field in the
response, and the migration UUID needs to be the pagination marker.

We propose to merge sort the results in compute api code once we get the
results back from all of the multiple cells, and results are sorted in
descending order by ['created_at', 'id'] keys.

Also, since we are going to add the ``uuid`` field to the response for the
``os-migrations`` API, we will also take this opportunity to add the migration
``uuid`` to the response for the
``GET /servers/{server_id}/migrations/{migration_id}`` and
``GET /servers/{server_id}/migrations`` server migrations APIs.


Alternatives
------------

None

Data model impact
-----------------

A database index will be added on migrations.updated_at to improve the
performance of filtering migrations by 'changes-since' parameter.

REST API impact
---------------

The proposal would add API microversion for getting several migrations using
general pagination mechanism. New optional parameters `limit`, `marker`,
and `changes-since` will be added to GET /os-migrations request.

Generic request format ::

    GET /os-migrations?limit={limit}&marker={migration_uuid}

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
            "id": 1,
            "instance_uuid": "instance_id_123",
            "new_instance_type_id": 2,
            "old_instance_type_id": 1,
            "source_compute": "compute1",
            "source_node": "node1",
            "status": "Done",
            "updated_at": "2012-10-29T13:42:02.000000",
            "uuid": "12341d4b-346a-40d0-83c6-5f4f6892b650"
        },
        {
            "created_at": "2013-10-22T13:42:02.000000",
            "dest_compute": "compute20",
            "dest_host": "5.6.7.8",
            "dest_node": "node20",
            "id": 2,
            "instance_uuid": "instance_id_456",
            "new_instance_type_id": 6,
            "old_instance_type_id": 5,
            "source_compute": "compute10",
            "source_node": "node10",
            "status": "Done",
            "updated_at": "2013-10-22T13:42:02.000000",
            "uuid": "56781d4b-346a-40d0-83c6-5f4f6892b650"
        },
        {
            "created_at": "2013-10-22T13:45:02.000000",
            "dest_compute": "compute21",
            "dest_host": "5.6.7.8",
            "dest_node": "node21",
            "id": 3,
            "instance_uuid": "instance_id_4561",
            "new_instance_type_id": 6,
            "old_instance_type_id": 5,
            "source_compute": "compute10",
            "source_node": "node10",
            "status": "Done",
            "updated_at": "2013-10-22T13:45:02.000000",
            "uuid": "56791d4b-346a-40d0-83c6-5f4f6892b650"
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
            "id": 1,
            "instance_uuid": "instance_id_123",
            "new_instance_type_id": 2,
            "old_instance_type_id": 1,
            "source_compute": "compute1",
            "source_node": "node1",
            "status": "Done",
            "updated_at": "2012-10-29T13:42:02.000000",
            "uuid": "12341d4b-346a-40d0-83c6-5f4f6892b650"
        },
        {
            "created_at": "2013-10-22T13:42:02.000000",
            "dest_compute": "compute20",
            "dest_host": "5.6.7.8",
            "dest_node": "node20",
            "id": 2,
            "instance_uuid": "instance_id_456",
            "new_instance_type_id": 6,
            "old_instance_type_id": 5,
            "source_compute": "compute10",
            "source_node": "node10",
            "status": "Done",
            "updated_at": "2013-10-22T13:42:02.000000",
            "uuid": "56781d4b-346a-40d0-83c6-5f4f6892b650"
        }
    ],
    "migrations_links": [
        {
            "href": "https://openstack.example.com/v2.1/os-migrations?limit=2&marker=56781d4b-346a-40d0-83c6-5f4f6892b650",
            "rel": "next"
        }
    ]
    }

3) Get all migrations after uuid=12341d4b-346a-40d0-83c6-5f4f6892b650 ::

    GET /os-migrations?marker=12341d4b-346a-40d0-83c6-5f4f6892b650

   Response ::

    {
    "migrations": [
        {
            "created_at": "2013-10-22T13:42:02.000000",
            "dest_compute": "compute20",
            "dest_host": "5.6.7.8",
            "dest_node": "node20",
            "id": 2,
            "instance_uuid": "instance_id_456",
            "new_instance_type_id": 6,
            "old_instance_type_id": 5,
            "source_compute": "compute10",
            "source_node": "node10",
            "status": "Done",
            "updated_at": "2013-10-22T13:42:02.000000",
            "uuid": "56781d4b-346a-40d0-83c6-5f4f6892b650"
        },
        {
            "created_at": "2013-10-22T13:45:02.000000",
            "dest_compute": "compute21",
            "dest_host": "5.6.7.8",
            "dest_node": "node21",
            "id": 3,
            "instance_uuid": "instance_id_4561",
            "new_instance_type_id": 6,
            "old_instance_type_id": 5,
            "source_compute": "compute10",
            "source_node": "node10",
            "status": "Done",
            "updated_at": "2013-10-22T13:45:02.000000",
            "uuid": "56791d4b-346a-40d0-83c6-5f4f6892b650"
        }
    ]
    }

4) Get all migrations after changes-since=2013-10-22T13:45:02.000000 ::

    GET /os-migrations?changes-since=2013-10-22T13:45:02.000000

.. note:: The provided time should be an ISO 8061 formatted time.
   ex 2013-10-22T13:45:02.000000, 2017-10-18T16:06:59Z

Response ::

    {
    "migrations":[
        {
            "created_at": "2013-10-22T13:45:02.000000",
            "dest_compute": "compute21",
            "dest_host": "5.6.7.8",
            "dest_node": "node21",
            "id": 3,
            "instance_uuid": "instance_id_4561",
            "new_instance_type_id": 6,
            "old_instance_type_id": 5,
            "source_compute": "compute10",
            "source_node": "node10",
            "status": "Done",
            "updated_at": "2013-10-22T13:45:02.000000",
            "uuid": "56791d4b-346a-40d0-83c6-5f4f6892b650"
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

Python-novaclient will be modified to handle the new microversion for
migration pagination support.

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
  Yikun Jiang

Other contributors:
  Zhenyu Zheng

Work Items
----------

* Create a new API microversion for getting several migrations using
  general pagination mechanism and time stamp filtering and adding a
  migration UUID field in the response.
* Modify the Nova client to handle the new microversion for migration
  pagination support.

Dependencies
============

None

Testing
=======

Would need new in-tree functional and unit tests.

Documentation Impact
====================

Docs needed for new API microversion and usage.

References
==========

 .. [1] Add uuid to migration table:
    https://review.openstack.org/#/c/496933/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Proposed
   * - Queens
     - Re-proposed
