..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Make checks before live-migration async
=======================================

https://blueprints.launchpad.net/nova/+spec/async-live-migration-rest-check

The existing nova live-migration operation is complex: verification of
the environment is required before accepting and triggering the live-migration.
This verification is done in a synchronous manner with several RPC calls that
must all be successful before the process can begin and the REST API layer can
respond. It would be better to make the checks asynchronous and have the REST
API respond with an immediate `202 - Accepted`.


Problem description
===================

The existing workflow for the environment verification required before a
live-migration involves several steps: an RPC call is made to the conductor
which triggers two more RPC calls to the relevant compute nodes. Only once
those are okay is there an RPC cast to trigger the migration and a response to
the HTTP request.


Use Cases
---------

A user doing a live migration would like to have a fast response to a
live-migration request and use the `instance-actions` service to get valid
status.

Proposed change
===============

Instead of doing all the checks in a block way, this spec proposes to record
the conductor's method with `wrap_instance_event` so it will be possible to
check live-migration status. Upon receiving a request for a live-migration
the Nova API will send an RPC cast to the conductor and then respond
immediately with the HTTP response. To separate blocking and non-blocking
live-migration types new method will be introduced to conductor's RPC API:
* migrate_server - existing general method for cold migration, resize and
live-migration. This will continue providing existing blocking behaviour, by
sending RPC call from Nova API to conductor.
* live_migrate_server - new method for live-migration only. This method will
implement non-blocking checks by using rpc cast from the Nova API layer.
Both methods should be decorated with `wrap_instance_event`, so events will be
recorded to database for blocking and non-blocking paths too.


Alternatives
------------

Leave things as they are. Another alternative would be to switch to
non-blocking rpc cast without maintaining previous behavior and bumping Nova
REST API microversion.

Data model impact
-----------------

None

REST API impact
---------------

As this change will cause verification checks to be done in the background, the
number of cases in which the live-migration API will respond with
`badRequest(400)` will be limited to receipt of bad input. REST API
microversion should be bumped, to retain possibility of switching to previous
behaviour.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

Users should check live-migration status, using `instance-actions` operation.

Performance Impact
------------------

Nova REST API method becomes non-blocking, which should increase overall
throughput of the API layer. At the same time more writes to database should be
added(writing instance actions details on conductor's side).

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
  tdurakov

Other contributors:
  rpodolyaka

Work Items
----------

* Add `wrap_instance_event` decorator to conductor's methods
* Make live-migration checks nonblocking
* Bump Nova REST API version.


Dependencies
============

None


Testing
=======

Test for checking that conductor's part of live-migration is recorded by
instance-actions should be added to tempest. Also code should be covered by
unit and functional tests too.


Documentation Impact
====================

As this change changes workflow, docs should be updated. It's needed to
highlight to the end user that it's required to check live-migration process
over `instance-actions`.

References
==========

* https://review.openstack.org/#/c/314932/ - PoC


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
