..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Show Scheduler Hints in Server Details
======================================

https://blueprints.launchpad.net/nova/+spec/show-scheduler-hints-in-server-details

Nova currently lacks a straightforward way to expose ``scheduler hints``
associated with a server. This proposal suggests extending existing Nova's
API to allow users to retrieve this information when it is available.

Problem description
===================

Scheduler hints can be specified at server creation time and can influence
placement decisions based on the user-provided configuration. These hints are
stored in the Nova's database and can be later considered by the scheduler
during a server migration. Without this information beforehand, an API user
can choose an invalid destination host for a migration request, and face
difficulties to understand the real cause of the failure.

Use Cases
---------

- As an operator, I want to retrieve more details about a server creation
  request, which includes the associated ``scheduler_hints``.

- As a cloud admin, I want to check more informations associated to all running
  servers, including their scheduler hints, in order to build an migration
  plan from a host.

- An optimization service like Watcher `[1]`_ would benefit from additional
  placement constraints, like scheduler hints, from all instances of a host
  in order to build a more concrete action plan to optimize the workload
  balance across the cluster. Without this information, Watcher could propose
  a solution that contains lots of server migration actions that violate some
  constraints. E.g.: Watcher would not account that a host is an invalid
  destination for a server that was created with a ``different_host`` scheduler
  hint.

Proposed change
===============

Code changes
------------

Extend the API response for ``GET /servers/{server_id}`` and the
``GET /servers/detail`` to include information about the scheduler hints.

Add a new entry in the API response with the key ``scheduler_hints``,
containing all persisted scheduler hints associated with the corresponding
server. The value format will follow the same json schema defined in server
creation request `[2]`_. If a server has no information about scheduler
hints, the value will be set to ``{}``.

Both openstack client and openstack sdk will be updated to support the new API
and display the new field added.

Alternatives
------------

User driven instance metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Users could aditionally store scheduler hints information in instance
metadata. This would allow them to query this inforamation later when needed.
The drawbacks are that it duplicates this information in nova database and
also requires an additional manual step from user's side.

Data model impact
-----------------

None.

REST API impact
---------------

The following change will be introduced in a new API microversion:

* GET ``/servers/{server_id}``

  Show Server Details

  Return Code(s): 400, 401, 403 (no changes)

  Proposed JSON response addition:

  .. code-block::

      {
          "server": {
              ...
              "scheduler_hints": {
                  "group": "af16eb84-88fe-4cc4-b558-1752cbe8cb15",
                  "same_host": "6605bff6-86b9-4824-b35b-a6b3c4c0e717"
              },
              ...
          }
      }

* GET ``/servers/detail``

  List Servers Detailed

  Return Code(s): 400, 401, 403 (no changes)

  Proposed JSON response addition:

  .. code-block::

      {
          "servers": [
              {
                  ...
                  "scheduler_hints":{
                    "group":"dc0ca1ef-7e0b-4cb5-89aa-b2069f8b8a8a",
                    "different_host":"6dffb036-d020-4630-b467-334400a050ca"
                  },
                  ...
              }
          ]
      }

The default policy of the new field will be ``project_reader_or_admin``
to match with the existing ``/servers/detail`` policy.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

A new field with scheduler hints information will be added in the output of
the commands ``Show Server Details`` and ``List Servers Detailed``, in both
openstack client and openstack sdk.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.


Developer impact
----------------

None.


Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dviroel

Feature Liaison
---------------

None.

Work Items
----------

* Add a new field to the server details response in a new microversion,
  and populated it with the persisted scheduler hints.
* Extend existing unit and functional tests, including API sample tests.
* Extend existing scheduler_hints and show server details tempest tests to
  validate that the new microversion contains ``scheduler_hints`` information.
* Update API documentation, including API samples in API Reference.
* Update openstack client and openstack sdk to support the new microversion
  and to show the new field.

Dependencies
============

None.

Testing
=======

Existing unit, funcional, API sample and tempest tests can be extended to
validate that the new microversion contains ``scheduler_hints`` information.
If needed, new tests can be added to properly cover other scenarios.


Documentation Impact
====================

* API Reference
* REST API Version History
* openstack client and openstack sdk documentation

References
==========

* Previous spec proposal for this blueprint:
    https://review.opendev.org/c/openstack/nova-specs/+/440580

.. _`[1]`: https://docs.openstack.org/watcher/latest/
.. _`[2]`: https://github.com/openstack/nova/blob/master/nova/api/openstack/compute/schemas/servers.py

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2025.1 Epoxy
     - Introduced
