..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================================================
Fix resource tracking for migration operations (live, cold, rebuild)
====================================================================

https://blueprints.launchpad.net/nova/+spec/migration-fix-resource-tracking

Resource tracking for operations that move instances between compute hosts is
broken in Nova. The fix requires some refactoring and tweaking of the data
model so it's discussed in a spec. It's really about fixing of several long
standing bugs.

Problem description
===================

Resource tracking for operations that move instances between compute hosts is
broken. Those operations are:

* Migrate/resize
* Live migrate
* Rebuild/Evacuate

There are 2 problems

1. In order for resources to be tracked properly in a Nova cloud, whenever a
   request to build an instance gets to a compute host, a resource claim needs
   to be done holding a global process-wide lock. Failure to do this can result
   in wrong resource allocation that will not follow the policy cloud
   administrator wants, or in some cases, failure to launch an instance.
   Live-migrate and rebuild code paths currently do not use claims at all.

2. Some resources like NUMA topology and PCI devices cannot be simply
   calculated from the flavor in case of a move operations, and must be
   persisted after a successful claim, as they don't simply refer to a count
   of a single uniform resource (like a vCPU) but refer to an actual unique
   device/resource. [1]_

Use Cases
----------

Live/cold migrate and rebuild, but it's essentially a bug fix.

Project Priority
-----------------

As this relates to resource tracking - this is deemed as a part of the
scheduler priority effort.


Proposed change
===============

The changes aim at solving the two issues described above.

First step is to make evacuate and live-migrate code paths do claims before
starting the work (and also abort claims on failure). This is really bug-fixing
work. It will also move creating migration entries proposed by [2]_ to happen
as part of the claim.

Second, we will add additional data to track resources after being claimed for
a migration, we will add a migration_context column to the instance_extra table
and store the claimed resources there to be used for tracking migration
resources. Part of this work will mean also changing the resource tracker to
consider these when doing resource tracking. Initially it will only contain the
'new' NUMA topology.


Alternatives
------------

None really.

Data model impact
-----------------

Add a single column to the instance_extra table called migration_context.
This column is NULL by default, or contains a serialized MigrationContext
object, which we will also add as part of this work.

We'll be accessing this data on the Instance object, in the same fashion other
data stored in the instance_extra is accessed.

REST API impact
---------------

None

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

Migrate and evacuate will need to acquire global locks to update tracked
resources. It is likely that performance impact of this will be negligible.

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
  <ndipanov>

Work Items
----------

* Add a new column to the instance_extra column and related objects code.
* Change live_migration to claim resources using a call to
  ResourceTracker.live_migrate_claim() (which we will add) likely as part of
  the check_can_live_migrate_destination compute service method. Move the
  creation of the migration object to this method or additionally flip a flag
  that lets the resource tracker know to consider it for resource calculations,
  in case we deem necessary to create migration records elsewhere.
* Do the similar as above for rebuild, claim happening in the rebuild_instance
  compute manager method.
* Make sure that the newly added claim methods, persist the newly calculated
  data (NUMA topology initially).


Dependencies
============

* We rely on [2]_ to introduce creation of migration objects for live-migrate
  and rebuild operations.


Testing
=======

The scope of this work will focus on solid unit testing of the functionality
added/changed. This area is a good target for functional testing, however as
with all similar pieces of functionality that need different execution threads
to hit interesting edge cases, it is difficult to come up with repeatable
automated tests.


Documentation Impact
====================

None


References
==========

.. [1] Discission on the following
       `patch <https://review.openstack.org/#/c/163440/>` offers some more
       details on this.
.. [2] https://blueprints.launchpad.net/nova/+spec/robustify-evacuate

History
=======

Optional section for liberty intended to be used each time the spec
is updated to describe new design, API or any database schema
updated. Useful to let reader understand what's happened along the
time.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
