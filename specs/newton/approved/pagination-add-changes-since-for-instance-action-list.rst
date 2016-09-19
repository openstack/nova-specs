..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================================================
Add pagination and changes-since filter support for os-instance-actions API
===========================================================================

https://blueprints.launchpad.net/nova/+spec/pagination-add-changes
-since-for-instance-action-list

This blueprint add `limit` and `marker` optional
parameters to GET /os-instance-actions request to support pagination.

This blueprint also add `changes-since` optional parameters to
GET /os-instance-actions request to support filtering response data by
updated time.

Problem description
===================

Currently, os-instance-actions  API does not support pagination.
As in production deployment the number of instance action records
can be also very large query them all can lead to performance
bottleneck, it will be very useful to support pagination.

Also, os-instance-actions API does not support filter the migration
record by last updated time. As for production deployment, an instance
can be up for a very long time, and the number of migration records
will also be very big. It will be very useful to support filter by
last update time.

Use Cases
---------

For large scale production deployment, the administrator can use
pagination and lastest updated time filter to have more efficient
database query.

Proposed change
===============

Add an API microversion that allows to get several migrations using
general pagination mechanism with the help of `limit` optional
parameters to GET /os-instance-actions  request. And add filter with
the help of `changes-since` optional parameter to GET /os-instance-actions
request.

* **limit**: Maximum number of instance actions to display. If limit == -1,
  all migrations will be displayed. If limit is bigger than `osapi_max_limit`
  option of Nova API, limit `osapi_max_limit` will be used instead.

* **marker**: The last instance's action timestamp of the previous page.
  Displays list of migrations after "marker".


Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

The proposal would add API microversion for getting several migrations using
general pagination mechanism. New optional parameters `limit`,
`marker` and `changes-since` will be added to
GET /os-instance-actions request.

Generic request format ::

    GET /os-instance-actions?limit={limit}&marker={kp_name}

1) Get all instance actions ::

    GET /os-instance-actions

   Response ::

    {
      "instanceActions": [
        {
          "instance_uuid": "ccc6afd4-2484-4c32-bd42-70cacf571a0e",
          "user_id": "7b2ddda599f74f9aabfe554a978aeca2",
          "start_time": "2015-10-30T03:20:13.000000",
          "request_id": "req-11ac94e9-8a6e-41bc-81ac-507fc38a7e50",
          "action": "reboot",
          "message": null,
          "project_id": "0721e55af7904e3b83f1276cd7ef769d"
        },
        {
          "instance_uuid": "ccc6afd4-2484-4c32-bd42-70cacf571a0e",
          "user_id": "7b2ddda599f74f9aabfe554a978aeca2",
          "start_time": "2015-10-30T03:16:34.000000",
          "request_id": "req-c3053bed-f1f0-4cb3-bde0-21cca81f0543",
          "action": "start",
          "message": null,
          "project_id": "0721e55af7904e3b83f1276cd7ef769d"
        },
        {
          "instance_uuid": "ccc6afd4-2484-4c32-bd42-70cacf571a0e",
          "user_id": "7b2ddda599f74f9aabfe554a978aeca2",
          "start_time": "2015-10-30T03:16:10.000000",
          "request_id": "req-aef8b118-a8b6-4d53-bfff-c81f035cda2b",
          "action": "stop",
          "message": null,
          "project_id": "0721e55af7904e3b83f1276cd7ef769d"
        },
        {
          "instance_uuid": "ccc6afd4-2484-4c32-bd42-70cacf571a0e",
          "user_id": "7b2ddda599f74f9aabfe554a978aeca2",
          "start_time": "2015-10-30T02:10:14.000000",
          "request_id": "req-79fa95a3-ce44-4554-bf66-b6731353866d",
          "action": "create",
          "message": null,
          "project_id": "0721e55af7904e3b83f1276cd7ef769d"
        }
      ]
    }

2) Get no more than 2 instance actions ::

    GET /os-instance-actions?limit=2

    Response ::

    {
      "instanceActions": [
        {
          "instance_uuid": "ccc6afd4-2484-4c32-bd42-70cacf571a0e",
          "user_id": "7b2ddda599f74f9aabfe554a978aeca2",
          "start_time": "2015-10-30T03:20:13.000000",
          "request_id": "req-11ac94e9-8a6e-41bc-81ac-507fc38a7e50",
          "action": "reboot",
          "message": null,
          "project_id": "0721e55af7904e3b83f1276cd7ef769d"
        },
        {
          "instance_uuid": "ccc6afd4-2484-4c32-bd42-70cacf571a0e",
          "user_id": "7b2ddda599f74f9aabfe554a978aeca2",
          "start_time": "2015-10-30T03:16:34.000000",
          "request_id": "req-c3053bed-f1f0-4cb3-bde0-21cca81f0543",
          "action": "start",
          "message": null,
          "project_id": "0721e55af7904e3b83f1276cd7ef769d"
        }
      ]
    }


Request format ::

    GET /os-instance-actions?changes-since=2015-10-30T03:16:10.000000"

Response ::

    {
      "instanceActions": [
        {
          "instance_uuid": "ccc6afd4-2484-4c32-bd42-70cacf571a0e",
          "user_id": "7b2ddda599f74f9aabfe554a978aeca2",
          "start_time": "2015-10-30T03:20:13.000000",
          "request_id": "req-11ac94e9-8a6e-41bc-81ac-507fc38a7e50",
          "action": "reboot",
          "message": null,
          "project_id": "0721e55af7904e3b83f1276cd7ef769d"
        },
        {
          "instance_uuid": "ccc6afd4-2484-4c32-bd42-70cacf571a0e",
          "user_id": "7b2ddda599f74f9aabfe554a978aeca2",
          "start_time": "2015-10-30T03:16:34.000000",
          "request_id": "req-c3053bed-f1f0-4cb3-bde0-21cca81f0543",
          "action": "start",
          "message": null,
          "project_id": "0721e55af7904e3b83f1276cd7ef769d"
        },
        {
          "instance_uuid": "ccc6afd4-2484-4c32-bd42-70cacf571a0e",
          "user_id": "7b2ddda599f74f9aabfe554a978aeca2",
          "start_time": "2015-10-30T03:16:10.000000",
          "request_id": "req-aef8b118-a8b6-4d53-bfff-c81f035cda2b",
          "action": "stop",
          "message": null,
          "project_id": "0721e55af7904e3b83f1276cd7ef769d"
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
