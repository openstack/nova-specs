..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Add host info to instance action events
=========================================

Currently, the ``instance action event`` record does not include
the ``host`` information of the action event occurs. Including this
field to the ``instance action event`` record will make it easier
for admins to locate where error happens and be able to solve the
problem faster.

This blueprint proposes to add ``host`` field to ``InstanceActionEvent``
object and related API responses.

https://blueprints.launchpad.net/nova/+spec/add-host-to-instance-action-events

Problem description
===================

Currently, the admins can use instance action API to look up the instance
actions info, it is very useful for admins and operators. But the host
info of events are not recorded and not exposed to user.

This host info helps admins to find the host of events occuring, especially,
when some failed events happened, the admins can find the failed host and log
as soon as possible.

Use Cases
---------

As a upper-layer management software admins, I want to query the host of
failed events occuring as soon as possile, and then I can find more system
status and log info in this host.

Proposed change
===============

Currently, the instance action event record has a ``host`` column on it [1]_,
we just need record the host info when the event is recorded and add the
host field in the response.

* Add ``host`` field to ``InstanceActionEvent`` object.

* Record the host info when the event is recorded.

* Add an API microversion to the
  ``GET /servers/{UUID}/os-instance-actions/{REQ_ID}`` to include ``host`` in
  the response.

Alternatives
------------

As alternative the upper-layer management software (or the admins) can listen
to the versioned instance notifications [2]_, and the notification contains
the node and the host of the instance.

Data model impact
-----------------

Add a new ``host`` field to ``InstanceActionEvent`` object, to record the
host that the event occurs on.

REST API impact
---------------

Add a new microversion to
``GET /servers/{server_id}/os=instance-actions/{req_id}`` API to include
the ``host`` field for admin and an obfuscated hashed host id ``hostId`` for
admin and non-admin users.

* For admin users::

    {
      "instanceAction": {
        "action": "stop",
        "events": [
          {
            "event": "compute_stop_instance",
            "finish_time": "2017-12-07T11:07:06.431902",
            "result": "Success",
            "start_time": "2017-12-07T11:07:06.251280",
            "traceback": null,
            "host": "host1",
            "hostId": "8a8d66db9eed58f2b1283d23acc9a32691290b603a716d81d8ed8c4e"
            }
        ],
        "instance_uuid": "b48316c5-71e8-45e4-9884-6c78055b9b13",
        "message": "",
        "project_id": "6f70656e737461636b20342065766572",
        "request_id": "req-3293a3f1-b44c-4609-b8d2-d81b105636b8",
        "start_time": "2017-12-07T11:07:06.088644",
        "updated_at": "2017-12-07T11:07:06.431902",
        "user_id": "fake"
      }
    }


* For non-admin users::

    {
      "instanceAction": {
        "action": "stop",
        "events": [
          {
            "event": "compute_stop_instance",
            "finish_time": "2017-12-07T11:07:06.431902",
            "result": "Success",
            "start_time": "2017-12-07T11:07:06.251280",
            "hostId": "8a8d66db9eed58f2b1283d23acc9a32691290b603a716d81d8ed8c4e"
          }
        ],
        "instance_uuid": "b48316c5-71e8-45e4-9884-6c78055b9b13",
        "message": "",
        "project_id": "6f70656e737461636b20342065766572",
        "request_id": "req-3293a3f1-b44c-4609-b8d2-d81b105636b8",
        "start_time": "2017-12-07T11:07:06.088644",
        "updated_at": "2017-12-07T11:07:06.431902",
        "user_id": "fake"
      }
    }


Security impact
---------------

The display of newly added ``host`` field will be controlled by the
same policy of ``traceback`` field, if the user is prevented by policy
an obfuscated-hashed-host-id will be displayed instead of hostname.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Yikun Jiang

Other contributors:
  Kevin Zheng

Work Items
----------

* Add a new ``host`` field to ``InstanceActionEvent`` object, to record the
  host that the event occurs on.
* Add a new microversion to
  ``GET /servers/{server_id}/os=instance-actions/{req_id}`` API to include
  the ``host`` field for admin and a ``hostId`` field for non-admin users.
* Adopt the new microversion in python-novaclient.
* Add related tests.

Dependencies
============

None

Testing
=======

Would need new in-tree functional and unit tests.

Documentation Impact
====================

Update the api reference to include this change.

References
==========

 .. [1] Add host and details column to instance_actions_events table:
    https://review.openstack.org/#/c/61441/
 .. [2] Existing versioned notifications in Nova:
    https://docs.openstack.org/nova/latest/reference/notifications.html#existing-versioned-notifications

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Proposed
