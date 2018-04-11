..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Allow abort live migrations in queued status
============================================

https://blueprints.launchpad.net/nova/+spec/abort-live-migration-in-queued-status

This blueprint adds support to allow abort live migrations in ``queued``
status.

Problem description
===================

The functionality of abort live migration was added in microversion 2.24 [1]_,
and currently only migrations in ``running`` status are allowed to be
aborted.

There is a config option ``max_concurrent_live_migrations`` that can be used
to control the max number of concurrent live migrations, the default value
is 1. When the number of live migration requests could be greater than the
max concurrent live migration configuration, there will be migrations wait
in queue. The migrations could remain in ``queued`` status for a very long
time depend on the queue length and the processing speed.

Admins may want to abort migrations in queue due to time consumption
considerations etc. It will be unreasonable to make admins wait until
the status turn to ``running`` before they can be aborted.

Use Cases
---------

Migrations could be stuck in ``queued`` status for a very long time
because of the migration queue length and processing speed. Admins
may want to abort migrations in queue due to time consumption considerations
etc.

Proposed change
===============

The whole change will be divided into two steps:

Step1 - Fix the problem of lack of queue
----------------------------------------

In the current implementation, the code that serializes the live migrations
on compute node uses a python semaphore, the value of the semaphore is set
to be ``CONF.max_concurrent_live_migrations``, each incoming migration will
try to acquire this semaphore, if the acquire succeed, the value of the
semaphore will decrease by one, and the status of the migration will turn
to status other than ``queued``. When the value decreased to 0, new incoming
migrations will be blocked(migration status will be ``queued``) until some of
the previous migration was finished(succeed, failed or aborted) and releases
the semaphore.

According to the above mentioned implementation, it is unable to abort a
migration in ``queued`` status as there is actually no QUEUE, so we are
not able to control the migrations blocked by the semaphore.

This spec will propose a design that can achieve the above mentioned goal:

* Using ``ThreadPoolExecutor`` from ``concurrent.futures`` lib instead of
  the current ``eventlet.spawn_n()`` + python ``Semaphore`` implementation.
  The size of the Thread Pool will be limited by
  ``CONF.max_concurrent_live_migrations``. When a live migration request
  came in, we submit the ``_do_live_migration`` calls to the pool, and it
  will return a ``Future`` object, we will use that later. If the pool is
  full, the new comming request will be blocked and kept in ``queued``
  status.

* Add a new ``_waiting_live_migration`` variable to the ``ComputeManager``
  class of the compute node, this will be a dict, and will be initialized
  as an empty dict. We will:

  1. Record the connection between ``migration_uuid`` and the ``Future``
     object when the thread is created in previous step, we will use
     ``migration_uuid`` as key and ``Future`` object as value in our dict.

  2. Remove the corresponding key/value the first thing if the thread
     successfully acquired the executor and enter
     ``_do_live_migration()`` [2]_. In this way, we will have a queue-like
     thing to store Futures and make it possible to get them by
     ``migration_uuid``.


Step2 - Allow abort live migrations in queued status
----------------------------------------------------

After the modification proposed in step 1, we will be able to get threads
blocked by ``migration_uuid`` and then we can abort them:

* First check whether the provided ``migration_uuid`` is in the
  ``_waiting_live_migration`` dict or not, if it is not in, then it will
  be in status other than ``queued``, we can switch to the workflow as is
  today.

* If the provided ``migration_uuid`` is in ``_waiting_live_migration`` dict
  then get the corresponding ``Future`` object and call ``cancel()`` method
  of the ``ThreadPoolExecutor``.

* If the cancel call succeed, we perform roll back and clean ups for the
  migration in ``queued`` status. The cancel call will return ``False``
  if the provided ``Future`` object is currently executing, which means the
  provided thread is no longer blocked, so we can switch to the workflow of
  abort migration in ``running`` status as is today.

* Add an API microversion to
  ``DELETE /servers/{id}/migrations/{migration_id}`` API to allow abort
  live migration in ``queued`` status. If the microversion of the request
  is equal or beyond the newly added microversion, API will check the
  ``instance.host's`` nova-compute service version and make sure it is
  new enough for the new support, if not, API will still return 400 as today.

* We will also add a cleanup to the pool when the compute manager is
  shutting down. This can simply be done by calling
  ``ThreadPoolExecutor.shutdown(wait=False)``.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

The proposal would add API microversion to
``DELETE /servers/{id}/migrations/{migration_id}`` API to allow abort live
migration in ``queued`` status. When request with API microversion larger
than the newly added microversion, the response will change from
``HTTP 400 BadRequest`` to ``HTTP 202 Accepted`` if the status of requested
live migration is in ``queued`` status.


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

Python-novaclient will be modified to handle the new microversion to
allow abort live migrations in ``queued`` status.

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

Compute API will still return 400 for trying abort a migration in
queued state if the compute service that the instance is running on
is too old.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Zhenyu Zheng

Work Items
----------

* Create a new API microversion to allow abort live migrations in
  ``queued`` status.
* Modify the Nova client to handle the new microversion.

Dependencies
============

None

Testing
=======

Would need new in-tree functional and unit tests.

Documentation Impact
====================

Docs needed for new API microversion and usage.

References
==========

.. [1] https://specs.openstack.org/openstack/nova-specs/specs/mitaka/implemented/abort-live-migration.html

.. [2] https://github.com/openstack/nova/blob/67f1c9889/nova/compute/manager.py#L6021

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Proposed
