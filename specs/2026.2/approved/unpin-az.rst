..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Unpin Availability Zone from an instance
========================================

https://blueprints.launchpad.net/nova/+spec/unpin-az

Currently, an instance is forever pinned to an availability zone if one was
selected at create time. This is often not ideal for long-running instances,
as changes in the deployment, emergency maintenance, or upgrades may require
moving workloads around. This spec aims to provide a way out.

Problem description
===================

Instance availability zone assignments are currently one-way and immutable.
This does not fit the operational reality where things may need to be moved
around for a variety of reasons over time.

The one exception to this is unshelve-to-host, which is only usable by
admins and requires non-trivial downtime and significant disruption to
the instance (loss of NVRAM, vTPM state, etc).

Use Cases
---------

- As an operator, I may need to move an instance to a different
  availability zone because of pending maintenance at a site or building.
- As an operator, I may need to move an instance from an AZ that is
  being retired to a new one because of an upgrade.
- As an application deployer in a position of elevated trust, I may
  need to move an instance to a different AZ than the one I originally
  selected in order to adapt to changing HA needs.
- As an application deployer I may need to reverse a decision to pin
  an instance to a given AZ without having to delete and recreate the instance.
- As an operator, I want to use Watcher to balance workloads with a
  strategy that may involve keeping AZ separation between specific
  workloads, but which can move workloads between AZs (with
  appropriate authorization) according to more complex rules.

Proposed change
===============

We currently show both the requested and current availability zone of
an instance, but do not allow either to be changed. The proposal here
is to allow the requested AZ (i.e. the ``pinned_availability_zone``
field) to be changed RESTfully in an update (``PUT``) request. Only
two transitions will actually be allowed:

1. Moving from a pinned AZ to an unpinned state
   (i.e. ``pinned_availability_zone`` is changed from some
   non-``null`` value to ``null``)
2. Moving from an unpinned state (i.e. ``pinned_availability_zone`` is
   ``null``) to a pinned state where the new AZ is the one the
   instance is currently in.  Specifically the
   ``pinned_availability_zone`` value can (only) move from ``null`` to
   the current value of ``OS-EXT-AZ:availability_zone``.

If the AZ is changed to a non-``null`` value that does not match the
current AZ, an HTTP 409 Conflict response will be returned. The
ability to go from one AZ directly to another (even if current) AZ is
not allowed because we do not want to further support moving the
instance (via forced migration) between AZs and fixing up the
inconsistency afterwards. This is in support of a potential further
optimization for move operations themselves.

Since the AZ is normally something fully under the control of the
user, this change will be controlled only by the policy for regular
server update. It is *possible* that admins may want to limit this
ability, but it seems to make little sense and further complicates the
interoperability picture if this can be disabled. This does not imply
any additional ability to move an instance than a user currently has,
only that the AZ pin can be dropped before such an operation is
initiated. In other words: moving from one host to another
specifically, or generally to "some other host" (outside of a resize)
is something only an admin or otherwise privileged user can do
regardless of this ability to unpin an instance from an AZ.

The ``pinned_availability_zone`` for an instance is purely a
reflection of the restriction that will be provided "the next time
this is scheduled." It is not something the cell infrastructure
(i.e. the compute service) even knows about and thus has little
relation to the current state of the instance. Thus, this update will
be allowed at any time with the instance in any state.

Further optimization
--------------------

In the future, we should add the ability for move operations to
specifically move an instance to a specific AZ (i.e. the AZ equivalent
of target host). Since users do not have the (default) ability to use
the pure migration APIs (live or cold) even this would not enable
simple "move me to another AZ" operations on their own.

This spec does not include this work, and only opens the workflow of
unpin-move-repin for cases where this is allowed (i.e. regular users
can only move via resize).

Alternatives
------------

One alternative is to make this an instance action, although this
rejected because instance actions are not RESTful and this is a very
easy thing to do in a PUT request.

Another alternative would be to *only* allow migrating of an instance
to a specific AZ, although this does not address the use case of
*just* unpinning an instance from an existing AZ.

Data model impact
-----------------

No impact.

REST API impact
---------------

In a new microversion, we will provide mutability of the
``pinned_availability_zone`` field via ``PUT
/servers/{server_id}``. Normal response code will be HTTP 200.
The following cases will generate an HTTP 409 Conflict error:

- Attempting to change from ``null`` to an AZ that does not match
  the current location of the instance (which would also cover the
  case of providing an invalid AZ name)
- Attempting to change from a non-``null`` value to another
  non-``null`` value

The "unpin" operation would be::

  PUT /servers/{server_id}
  X-OpenStack-Nova-API-Version: 2.XX

  {
      "server": {
          "pinned_availability_zone": null
      }
  }

and the re-pin operation would be::

  PUT /servers/{server_id}
  X-OpenStack-Nova-API-Version: 2.XX

  {
      "server": {
          "pinned_availability_zone": "us-east-1"
      }
  }


No additional schema changes are needed.

Security impact
---------------

The AZ is something users currently have control over at create time,
so this just extends that control to "day 2". It doesn't grant them
any additional ability to move the instance that they didn't have
before.

Notifications impact
--------------------

No notifications are affected. Since this change involves updating the
request spec and not the instance itself, the ``instance.update``
notification will not be triggered. Since there is no obvious existing
place to add triggering of changes to the request spec, doing so will
be considered outside the scope of this spec. Further, the (likely to
follow) migration operations would signal an actual change by way of
the ``scheduler.select_destination`` notification, which includes the
``RequestSpec.availability_zone`` field, making the change visible to
consumers.

Other end user impact
---------------------

None, other than being able to change this field

Performance Impact
------------------

None.

Other deployer impact
---------------------

Deployers will be able to more easily move instances between AZs after
this change.

Developer impact
----------------

None.

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Work Items
----------

#. Propose a change to make the value mutable in server update
#. Add tempest tests for the new behavior
#. Evaluate and modify openstack client as necessary to make this easy
   for users to use.

Dependencies
============

None.

Testing
=======

Unit and functional tests. A tempest test should be added to verify that the
value can be unset, reset to the current AZ, and not to any other AZ.

Documentation Impact
====================

The following files in `doc/source` will be updated:

- ``admin/availability-zones.rst``
- ``admin/aggregates.rst``
- ``user/availability-zones.rst``

Text reflecting the immutability of the field (or that selection is
only possible at create time) will be adjusted. Text will also be
added to explain the unpinning workflow, with the requirements for
re-pinning.

References
==========

* Nova 2026.2 PTG `discussion`_

.. _discussion: https://etherpad.opendev.org/p/nova-2026.2-ptg


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2026.2 Hibiscus
     - Introduced
