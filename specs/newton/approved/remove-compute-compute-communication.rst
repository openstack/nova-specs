..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Remove compute-compute communication in live-migration
======================================================

https://blueprints.launchpad.net/nova/+spec/remove-compute-compute-communication

Current live migration process uses direct rpc communication between nova
computes. This communication is a mix of blocking and non blocking requests,
so there is room for timeouts, and subsequent failures.

Problem description
===================

Existing Live migration process allows compute to communicate with each other
during pre/post/rollback and live-migration itself steps. This process is
tricky and leave place to different potential issues. Live migration uses both
blocking and non-blocking rpc requests, with cause potential timeouts in case
when one of step is not finished yet, and races between nodes, in case of
asynchronous rpc casts. Root cause of problems described above, is that compute
node operates both orchestration and functional logic that actually do live
migration. Another potential issue with existing process that post live
migration phase(post/rollback) methods could never be executed and it will be
impossible to say whether all steps were passed or not. This problem is also
result of mixing process orchestration and real logic. When request reaches
conductor following workflow is happened:

* check_can_live_migrate_destination - blocking rpc call from conductor to
  destination compute to check possibility of schedulled migration. Before
  sending response to conductor, destination node sends following request to
  the source compute node.

* check_can_live_migrate_source - blocking rpc call from destination compute to
  source compute to check possibility of schedulled migration.

* live_migration - non-blocking rpc cast from conductor to source compute that
  actually triggers live-migration. After request is received by source compute
  node and before live migration actually starts, following request is sended
  to destination node.

* pre_live_migration - blocking rpc call from source compute to destination to
  prepare destination host for ongoing migration.

After steps described above 2 scenarios could happen:

* live-migration succeeded

* live-migration failed

In case of success following workflow will happen:

* post_live_migration_at_destination - non-blocking rpc cast from source
  compute to destination, to finish process

In case of failure:

* rollback_live_migration_at_destination - non-blocking rpc cast from source to
  destination compute to clean up resources after failed attempt


Use Cases
---------

Main use case to be covered is live migration process. This change will be
transparent from deployer/end user point of view.

Proposed change
===============

Refactor existing rpc communication during live migration, to get rid of
compute to compute rpc requests. Instead of it make process to be operated by
conductor.

To implement this create new rpc methods:

* post_live_migration_at_source finishes process on destination node in case
  of success

* rollback_live_migration_at_source - cleans up node in case of live-migration
  failure.

All rpc methods above should implement following pattern a.k.a. lightweight
rpc-calls: client sends blocking rpc call to service, once request is received
service spawns new greenlet to process it and responds to caller immediately.
This approach assures caller that request was delivered to service, and doesn't
block caller exucution flow.

Conductor in this case will be responsible for all preparations and checks to
be done before live migration, and rollback/post live-migration operations.
Proposed workflow:

* check_can_live_migrate_destination - blocking rpc call from conductor to
  destination compute to check possibility of schedulled migration.

* check_can_live_migrate_source - blocking rpc call from conductor to source
  compute to check possibility of schedulled migration.

* pre_live_migration - blocking rpc call from conductor to destination
  compute to prepare destination host for ongoing migration.

* live_migration - non-blocking rpc cast from conductor to source compute that
  actually triggers live-migration

After steps described above 2 scenarios could happen:

* live-migration succeeded

* live-migration failed

In case of success following workflow will happen:

* post_live_migration_at_source - non-blocking rpc cast from conductor to
  source compute after migration finished

* post_live_migration_at_destination - non-blocking rpc cast from conductor to
  destination compute

In case of failure:

* rollback_live_migration_at_source - non-blocking rpc cast from conductor to
  source compute to clean up resources after failed attempt

* rollback_live_migration_at_destination - non-blocking rpc cast from conductor
  to destination compute to clean up resources after failed attempt.

The main difference between proposed change and existing workflow are:

* instead of sequential blocking rpc calls from conductor to destination
  compute and then from it to source compute during checks before
  live-migration, spec proposes to do request from conductor to destination
  compute and from conductor to source compute in independent manner.
  So the possibility of timeout will be reduced. Also this change sets
  conductor as owner of live-migration process.

* pre_live_migration is done first before live_migration rpc cast is called

* conductor manages post/rollback for live-migration.

Alternatives
------------

Leave things as is, and not to change this communication. Another alternative
would be to go with fully non-blocking approach, using kind of state-machine
for switching between steps during live-migration.

Data model impact
-----------------

None

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

Several blocking rpc calls are replaced with non-blocking requests

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

tdurakov

Other contributors:
rpodolyaka

Work Items
----------

* refactor existing code to make it compatible with new rpc methods
* implement new rpc methods

Dependencies
============

None

Testing
=======

Standart unit-tests coverage, upgrade compatibility testing


Documentation Impact
====================

None

References
==========

* https://etherpad.openstack.org/p/mitaka-nova-priorities-tracking
* https://review.openstack.org/#/c/291161/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
