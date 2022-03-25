..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
soft-delete instance actions
============================

https://blueprints.launchpad.net/nova/+spec/soft-delete-instance-actions

This spec is mainly a reminder of actions that have to be taken to implement
the soft-delete of instance actions table when an instance is soft-deleted

Problem description
===================

Currently when an instance is soft-deleted the related instance actions are not
soft-deleted to allow the operator to get the history of actions taken on the
instance, especially who soft-deleted the instance.

This is not an issue as such but we are inconsistent on database level because
instance is marked as deleted but not the actions. We would like to improve
the consitency.

Use Cases
---------

* As a user I still want to be able to retrieve instance actions of a soft
  deleted instance.

* As an operator I want the instance actions to be soft-deleted when an
  instance is deleted.

Proposed change
===============

**Change how the instance action are fetched**

We must change the database queries that fetch instance action to read soft
deleted instance actions too.

By doing that we will be able to get instance actions of a soft-deletd instance
before and after this spec is implemented.

**Change on instance soft-deleting**

When we soft-delete an instance we have to soft-delete all the instance actions
tables (instance_actions, instance_actions_events) referencing the soft-deleted
instance.

**Change on instance restore**

When restoring an instance we have to restore instance_actions and
instance_actions_events too.


**Impacts on nova-manage**

* nova-manage db archive_deleted_rows

There is no impact on archiving because the filter on deleted column is applyed
on instances table only. Data on children tables are selected according to the
selected instances.
It means that in shadow tables instance actions are not soft deleted, data are
basically moved from main table to shadow table.

* nova-manage db purge

When using the purge command with the --before flag the filter is applied on
deleted_at column for all tables except instance_actions and
instance_actions_events for which the filter is applied on updated_at column.

So we have to modify the purge behavior to filter on deleted_at and updated_at
columns for instance_actions and instance_actions_events tables.

Alternatives
------------

The proposed changes works without changing existing data, it means that we are
able to implement soft delete of instance action and make it works with the
already instance actions not soft deleted without changing the API.

We could add a command to nova-manage db that will update the existing instance
action that should be soft deleted. This implies an upgrade step which is much
more tricky than the proposed change.


Data model impact
-----------------

None

instance_actions and instance_actions_events are already implementing the
soft-delete feature so there is no need to change schema.

REST API impact
---------------

None

The API will continue to return both soft-deleted and not deleted actions.
As the deleted state is not returned in the api response it won't impact the
API.

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

None

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

None as long as we do not choose the alternative.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    pslestang

Other contributors:
    N/A

Feature Liaison
---------------

Feature liaison:
    N/A

Work Items
----------

* Modify the fetch on instance_actions instance_actions_events to read deleted
  rows too.

* soft delete instance_actions and instance_actions_events when soft deleting
  instances

* purge with --before on instance_actions and instance_actions_events should be
  done on deleted_at column too.

Dependencies
============

None

Testing
=======

Can be tested with unit and functional tests.
We should also verify if API sample tests need to be modified since this should
not have any visible api change.


Documentation Impact
====================

None

References
==========

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Yoga
     - Introduced
