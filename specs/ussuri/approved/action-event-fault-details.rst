..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
Add action event fault details
==============================

https://blueprints.launchpad.net/nova/+spec/action-event-fault-details

The blueprint proposes to add the fault details to the failed instance
action event.

Problem description
===================

Currently, the instance action event details that a non-admin owner of a
server sees do not contain any useful information about what caused the
failure of the action. For example, if we failed to cold migrate a server,
show the server's event info by
``openstack server event show <server> <request-id>`` that will be
recorded as:

  .. code-block:: json

    {
       "events": [
         {
           "finish_time": "2019-11-13T16:18:27.000000",
           "start_time": "2019-11-13T16:18:26.000000",
           "event": "cold_migrate",
           "result": "Error"
         },
         {
           "finish_time": "2019-11-13T16:18:27.000000",
           "start_time": "2019-11-13T16:18:26.000000",
           "event": "conductor_migrate_server",
           "result": "Error"
         }
       ]
    }

Obviously, from the response of the server event action, the user cannot
obtain the actual useful information.

If the server status is not **ERROR** but some operation failed, the user
cannot get the fault details either because `server faults`_ are only shown
for servers in **ERROR** or **DELETED** status. But instance actions can be
shown for a server in any status (and even for deleted servers since
microversion 2.21).

Use Cases
---------

As a non-admin user, I would like to know the details about the failure when
the server is not in **ERROR** status. Although I can't see the exact
``traceback``, at least I can do other attempts based on the details.

Proposed change
===============

In a new microversion, expose the ``details`` field in the Show Server
Action Details API:

* GET /servers/{server_id}/os-instance-actions/{request_id}

Add a new policy to control the visibility for a set of instance action
attributes, its default rule is 'rule:system_reader_api' (Legacy rule
is 'rule:admin_api').

The event "details" are the same as the ``fault.message`` that the user would
see when the server is in **ERROR** status. For NovaExceptions that would be
the actual exception message but for non-NovaExceptions it's just the
`exception class name`_.

Alternatives
------------

Add ``user_message`` field on NovaException which, if present, gets percolated
up to a new field similar to the ``details``. Perhaps this can be as painful
as documenting all the different error types.

Data model impact
-----------------

None. The ``details`` column was already in the ``instance_actions_events``
table, and it's a TEXT size column so it should be large enough to hold
exception fault messages.

REST API impact
---------------

In a new microversion, expose the ``details`` parameters in the following
API responses:

* GET /servers/{server_id}/os-instance-actions/{request_id}

  .. code-block:: json

    {
       "events": [
         {
           "finish_time": "2019-11-13T16:18:27.000000",
           "start_time": "2019-11-13T16:18:26.000000",
           "event": "cold_migrate",
           "result": "Error",
           "details": "No valid host was found."
         },
         {
           "finish_time": "2019-11-13T16:18:27.000000",
           "start_time": "2019-11-13T16:18:26.000000",
           "event": "conductor_migrate_server",
           "result": "Error",
           "details": "No valid host was found."
         }
       ]
    }

This only populates the value of the ``details`` attribute after checking
that the policy matches 'rule: system_reader_api'.

With the new microversion the "details" key is always returned with each
event dict but the value may be null because of old records or events that
did not fail.

Security impact
---------------

There is a chance for a security impact with this change because we could be
leaking sensitive information about the deployment to a non-admin end user,
but we already do through server faults so this shouldn't be *worse*.
Note `bug 1851587`_ about faults.

Add a new policy so that the deployer can decide whether to expose these
fault information to the end users.

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

The developers have to be careful about what information they put into
NovaExceptions which could leak sensitive information to a non-admin end user.

Upgrade impact
--------------

None. The new column in the database was already exist.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  brinzhang

Feature Liaison
---------------

Feature liaison:
  brinzhang

Work Items
----------

* Add ``details`` to the ``InstanceActionEvent`` object, and populating it,
  and the populating part requires some work.

  .. note:: The defined ``exception_to_dict`` function behavior is not normal
            in compute utils, it could mean leaking non-nova error details
            which is why exception_to_dict just uses the exception type as
            the message if it cannot format the value. Need to change the
            ``serialize_args`` decorator to pass a format_exc_val kwarg, and
            make it to be smarter. This will not be an obstacle to completing
            this blueprint.
* Modify the API to expose the ``details`` field in GET responses that expose
  instance action event.
* Add related tests
* Docs for the new microversion.

Dependencies
============

None

Testing
=======

* Add related unit test for negative scenarios.
* Add related functional test (API samples).

Tempest testing should not be necessary for this change.

Documentation Impact
====================

Update the API reference for the new microversion.

References
==========

[1] "Thoughts on exposing exception type to non-admins in instance action
    event" in ML
    http://lists.openstack.org/pipermail/openstack-discuss/2019-November/010775.html

.. _`server faults`:
   https://docs.openstack.org/api-guide/compute/faults.html#instance-faults

.. _`exception class name`:
   In the defined ``exception_to_dict`` function to do
   ``message = fault.__class__.__name__`` (Just avoid invalid link).
   https://github.com/openstack/nova/blob/56fc3f28e48bd9c6faf72d2a8bfdf520cc3e60d0/nova/compute/utils.py#100

.. _`bug 1851587`: https://bugs.launchpad.net/nova/+bug/1851587

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Introduced
