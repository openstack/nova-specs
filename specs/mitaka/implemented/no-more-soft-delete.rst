..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================
No more soft delete
===================

https://blueprints.launchpad.net/nova/+spec/no-more-soft-delete

There was widespread agreement at the YVR summit not to soft-delete any more
things. To codify this, we should remove the SoftDeleteMixin from NovaBase.

Problem description
===================

Soft deletion of rows imposes a management overhead to later delete or archive
those rows. It has also proved less necessary than initially imagined. We would
prefer additional soft-deletes were not added and so it does not make sense to
automatically inherit the `SoftDeleteMixin` when inheriting from NovaBase.

Use Cases
---------

As an operator, adding new soft deleted things means I need to extend my
manual cleanup to cover those things. If I don't, those tables will become
very slow to query.

As a developer, I don't want to tempt operators to read soft-deleted rows
directly. That risks turning the DB schema into an unofficial API.

As a developer/DBA, providing `deleted` and `deleted_at` columns on tables
which are not soft-deleted is confusing. One might also say it's confusing to
soft-delete from tables where deleted rows are never read.

Proposed change
===============

This spec proposes removing the `SoftDeleteMixin` from NovaBase and re-adding
it to all tables which currently inherit from NovaBase. The removal of
SoftDeleteMixin from those tables which don't need it will be left for future
work.

Alternatives
------------

We could not do this. This means we need an extra two columns on new tables
and it makes it slightly easier to start soft-deleting new tables.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  alexisl

Other contributors:
  None

Work Items
----------

* Remove `SoftDeleteMixin` from NovaBase.
* Add it to all models which inherited from NovaBase.

Dependencies
============

None.

Testing
=======

None.

Documentation Impact
====================

None.

References
==========

None.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
   * - Mitaka
     - Simplified and re-proposed
