..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================================
Graceful Shutdown of Nova Services Part 2: Task Tracking
========================================================

https://blueprints.launchpad.net/nova/+spec/nova-services-graceful-shutdown-part2-task-tracking

This spec implements Spec 2 of the `nova-services-graceful-shutdown`_ backlog
spec for the Nova service. Spec 1 introduced a second RPC server in compute
service to separate new requets from in-progress requests and time
based wait in services manager to finish the in-progress tasks. This spec
replaces the time based wait with a proper task-tracking system that track
the in-progress tasks and their completion with detailed logging.

Problem description
===================

In graceful shutdown part1, services manager ``graceful_shutdown()`` was added
with logic of hard code waiting for the configurable
``manager_shutdown_timeout`` seconds so that in-progress tasks can be finished
before service is stopped. This mechanism have two problems:

* Unnecessary delay: If no tasks are running or they are completed before
  the ``manager_shutdown_timeout``, the service still waits for the
  ``manager_shutdown_timeout``  seconds before shutdown is finished.

* Nova or Operators have no way to know which tasks are blocking shutdown,
  how long they have been running, or which ones are still not completed when
  service is shutdown due to timeout. If the timeout is not sufficient for
  some remaining tasks, we will just exit anyway without waiting.

Use Cases
---------

* As an operator, I want the service to exit as soon as its in-progress
  task finishes.

* As an operator, I want the detailed logs to know which tasks were running
  when shutdown is initiated, and which ones are still not completed when
  service is shutdown due to timeout. This will help them to estimate the
  graceful_shutdown_timeout in their deployment and also re-initiate the
  non-comleted operations.

Proposed change
===============

A task-tracking system will be introduced directly on service manager. It
consists of:

* Tasks will be tracked in a dictionary with info task name, start_time,
  request-id, and instance UUID (if they are associated with instance).

* Once shutdown is initiated, a boolean flag ``_shutdown_in_progress`` will
  bet set to ``True`` which will signal service manager to start logging the
  in-progress tasks.

* Once shutdown is initiated, it will stop submitting the new periodic tasks.
  The new non-periodic tasks will be handled by the RPC server shutdown, which
  will stop accepting any new tasks.

* The configurable ``manager_shutdown_timeout`` is the max time a service
  manager will wait for tasks to finish.

Tracked task categories
-----------------------

A few of the common method will be added for task tracking:

* _record_task_start() (name can be changed during implementation)
  will record the RPC call in a dict with task name, request_id,
  instance_uuid (if task is associated with instance).

* _record_task_end() will remove it from tasks tracking dict
  once task is finished.

* _wait_for_tasks will be called by the service manager graceful_shutdown()
  method to wait until all in-progress tasks are completed or timeout.

Nova has the two categories of tasks which need to be tracked separately
because of their different execution models.

.. note:: These two catagories are not the RPC call vs RPC cast. Those can
  be tracked once the RPC method is called and finish its execution.
  RPC cast does not return any response and RPC call complete its execution
  and return response via the reply queue. The reply queues are active during
  shutdown until RPC call send back the response.

Async tasks:
~~~~~~~~~~~~
   Some of the tasks are async for example, ``build_and_run_instance()``,
   ``snapshot_instance()``, and ``live_migration()`` and they submit the work
   to a thread pool executor and return the future object. The RPC call is
   returned as soon as it is submitted in thread pool and before the actual
   operation completes so tracking the RPC call is not the correct way. For
   these async tasks, tracking will check the actual task is completed via
   future.add_done_callback() method which allow to attaches a callable
   that will be executed automatically when a Future object is finished.
   Something like

.. code-block:: python

    key = _record_task_start(
        'build_instance', instance.uuid, context.request_id)
    try:
        future = utils.spawn_on(executor, work_fn, ...)
    except Exception:
        self._record_task_end(key)
        raise
    future.add_done_callback(
        functools.partial(_record_task_end, key))

Sync tasks:
~~~~~~~~~~~
   Most of the tasks are for example ``stop_instance()``, ``start_instance()``,
   ``reboot_instance()``, ``get_console_output()`` etc run synchronously.
   They perform all their work before the RPC request is returned. We have two
   ways to track them. 1. Record the tasks by decorating the each RPC methods
   will not be a good idea. We can have a common wrapper who can record/track
   these sync RPC requests.

   A new RPC endpoint wrapper will be added. When RPC dispatcher will send the
   RPC message to endpoint (service manager), the endpoint wrapper can record
   the tasks before calling the manager RPC method. That will looks like

   Not all the manager methods will be tracked by this wrapper. A few examples
   of such methods are long-running tasks in the background, tasks which are ok
   to be interrupted during shutdown. There will be a way to mark such methods
   as untracked so that TrackingEndpointWrapper will skip tracking them.
   Something like:

.. code-block:: python

    def untracked_rpc_method(fn):
        fn._skip_rpc_tracking = True
        return fn

    @utils.untracked_rpc_method
    def cache_images(self, context, image_ids):
        """Ask the virt driver to pre-cache a set of base images"""

    class TrackingEndpointWrapper:
        def __init__(self, manager):
            self._manager = manager

         def __getattr__(self, name):
             attr = getattr(self._manager, name)
             if getattr(attr, '_skip_rpc_tracking', False):
                 return attr

             @functools.wraps(attr)
             def _track_task(* args, ** kwargs):

                 if args:
                     request_id = getattr(args[0], 'request_id', None)

                 instance_uuid = None

                 if 'instance' in kwargs:
                     inst = kwargs['instance']

                     if hasattr(inst, 'uuid'):
                         instance_uuid = inst.uuid

                 key = self._manager._start_active_rpc_call(
                     name, instance_uuid, request_id)
                 try:
                     return attr
                 finally:
                     self._manager._finish_active_rpc_call(key)

             return _track_task

Waiting logic
-------------

The flow of waiting for the in-progress tasks will be:

#. If the tasks tracking dictionary is empty, logs the message and returns.
#. Otherwise, logs all in-progress task.
#. Enters a ``Condition.wait`` loop that will wake up either when all tasks
   are completed or at timeout.
#. On timeout, logs a warning listing all tasks still in progress and return.

All of the task tracking logging  will be started when
shutdown is initiated (based on ``_shutdown_in_progress`` flag) so normal
(non-shutdown) operations are silent/unchanged.

Periodic tasks
--------------

The oslo.service ``LoopingCall`` run on specific timer and end up
calling the call ``manager.periodic_tasks()`` which calls the oslo.service
run_periodic_tasks() which go through all the periodic tasks and run them.

During the graceful shutdown. We will check if ``_shutdown_in_progress`` is
true and will return immediately without calling run_periodic_tasks().

This ensures that no new periodic work is initiated after shutdown is initiated
but allow any existing running periodic task to complete.

.. code-block:: python

    def periodic_tasks(self, context, raise_on_error=False):
        """Tasks to be run at a periodic interval."""
        if self._shutdown_in_progress:
            LOG.debug('Skipping periodic tasks during graceful shutdown.')
            return
        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)

Alternatives
------------

None

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

There should not be any performance impact due to extra step if recording the
tasks. Tasks logging/wait etc are only in picture when shutdown is initiated.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:

gmaan

Other contributors:

None

Feature Liaison
---------------

None

Work Items
----------

* Add common task tracking framework methods.
* Audit the async tasks and track them as per the async tasks tracking
  mechanism.
* Add functional tests.

Dependencies
============

None

Testing
=======

* Unit and functional tests

Documentation Impact
====================

* Update documentation for the task tracking and logging info.

References
==========

* Backlog spec: https://specs.openstack.org/openstack/nova-specs/specs/backlog/approved/nova-services-graceful-shutdown.html

* Part 1:

  * Spec: https://specs.openstack.org/openstack/nova-specs/specs/2026.1/implemented/nova-services-graceful-shutdown-part1.html
  * Implementation: https://review.opendev.org/q/topic:%22bp/nova-services-graceful-shutdown-part1%22+status:merged

* PTG discussions:

  * https://etherpad.opendev.org/p/nova-2026.1-ptg#L860
  * https://etherpad.opendev.org/p/nova-2025.1-ptg#L413

.. _`nova-services-graceful-shutdown`: https://specs.openstack.org/openstack/nova-specs/specs/backlog/approved/nova-services-graceful-shutdown.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2026.2
     - Introduced
