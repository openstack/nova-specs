..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================================================
Add pagination and changes-since filter support for os-instance-actions API
===========================================================================

https://blueprints.launchpad.net/nova/+spec/pagination-add-changes-since-for-instance-action-list

This blueprint adds `limit` and `marker` optional
parameters to GET /os-instance-actions/{server_id} request to support
pagination.

This blueprint also adds `changes-since` optional parameter to
GET /os-instance-actions/{server_id} request to support filtering
response data by updated time.

Problem description
===================

Currently, os-instance-actions API does not support pagination.
As in production deployment the number of instance action records per
instance can be also very large and querying them all can lead to performance
bottleneck, it will be very useful to support pagination.

Also, os-instance-actions API does not support filtering the instance action
record by last updated time. As for production deployment, an instance
can be up for a very long time, and the number of instance action records,
such as migrate operations, will also be very big. And considering the
situation of malicious attacking in public cloud, the attacker do a lot of
operations on an instance deliberately, the instance action records will be
also huge, once attacker query these instance actions of the instance, will
also have some bad effects on other operations, we need pagination support to
minimize the impact. It will be very useful to support filter by last updated
time.

There is a problem about updated_at not actually being updated on the
instance action record [1]_. We propose to fix this issue by updating
instance actions' updated_at when action create or action event update [2]_.

Use Cases
---------

For long running deployments, the administrator can use
pagination and last updated time filter to have more efficient
database query.

Proposed change
===============

Add an API microversion that allows to get several instance actions using
general pagination mechanism with the help of `limit` optional
parameters to GET /os-instance-actions/{server_id} request. And add filter
with the help of `changes-since` optional parameter to GET
/os-instance-actions/{server_id} request.

* **limit**: Maximum number of instance actions to display. If limit is
  bigger than `[api]/max_limit` option of Nova API, limit `[api]/max_limit`
  will be used instead.

* **marker**: The last instance's action request_id of the previous page.
  Displays list of instance actions after "marker".

.. todo:: We need to decide if we would sort on the updated_at field or the
   created_at field when the changes-since parameter is specified. Since
   changes-since filters by the updated_at field, it might make the most sense
   to sort by the updated_at field. However, that would be inconsistent with
   how instances are sorted by default when the changes-since filter is used
   with listing instances. This is an implementation detail that can be
   discussed during code review.

Alternatives
------------

None

Data model impact
-----------------

A database index will be added on the ``(instance_uuid, updated_at)`` columns
in the ``nova.instance_actions`` table to improve the performance of filtering
instance actions by the 'changes-since' parameter.

REST API impact
---------------

The proposal would add API microversion for getting several instance actions
using general pagination mechanism. New optional parameters `limit`,
`marker` and `changes-since` will be added to
GET /os-instance-actions/{server_id} request.

Generic request format ::

    GET /os-instance-actions/{server_id}?limit={limit}&marker={request_id}

1) Get all instance actions ::

    GET /os-instance-actions/ccc6afd4-2484-4c32-bd42-70cacf571a0e

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

    GET /os-instance-actions/ccc6afd4-2484-4c32-bd42-70cacf571a0e?limit=2

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
      ],
      "links": [
          {
              "href": "https://openstack.example.com/v2.1/os-instance-actions?limit=2&marker=req-c3053bed-f1f0-4cb3-bde0-21cca81f0543",
              "rel": "next"
          }
      ]
    }

3) Get all instance actions after changes-since=2013-10-22T13:45:02.000000 ::
Request format ::

    GET /os-instance-actions/ccc6afd4-2484-4c32-bd42-70cacf571a0e?changes-since=2015-10-30T03:16:10.000000"

.. note:: The provided time should be an ISO 8061 formatted time.
   ex 2013-10-22T13:45:02.000000, 2017-10-18T16:06:59Z

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

Python-novaclient will be modified to handle the new microversion for
instance action pagination support.

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
  Zheng Zhenyu

Work Items
----------

* Create a new API microversion for getting several instance actions using
  general pagination mechanism and time stamp filtering.
* Modify the Nova client to handle the new microversion for instance actions
  pagination support.

Dependencies
============

This change depends on the fix of instance actions' updated_at bug. [2]_

Testing
=======

Would need new in-tree functional and unit tests.

Documentation Impact
====================

Docs needed for new API microversion and usage.

References
==========

 .. [1] Instance actions' updated_at dicussion:
    http://lists.openstack.org/pipermail/openstack-dev/2016-June/098299.html
 .. [2] Instance actions' updated_at bug:
    https://bugs.launchpad.net/nova/+bug/1719561

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
