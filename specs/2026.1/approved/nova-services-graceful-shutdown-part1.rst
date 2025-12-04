..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Graceful Shutdown of Nova Services: Part1
=========================================

https://blueprints.launchpad.net/nova/+spec/nova-services-graceful-shutdown-part1

This proposes the spec 1 of the graceful shutdown `backlog spec`_ for the
2026.1 cycle.

Nova services do not shut down gracefully. When services are stopped, it also
stops all the in-progress operations, which not only interrupt the in-progress
operations, but can leave instances in an unwanted or unrecoverable state. The
idea is to let services stop processing the new request, but complete the
in-progress operations before service is terminated.

Problem description
===================

Nova services do not have a way to shutdown gracefully means they do not wait
for the in-progress operations to be completed. When shutdown is initiated,
services wait for the RPC server to stop and wait so that they can consume all
the existing request messages (RPC call/cast) from the queue, but the service
does not complete the operation.

Each Nova compute service has a single worker running and listening on a single
RPC server (topic: compute.<host>). The same RPC server is used for the new
requests as well as for in-progress operations where other compute or conductor
services communicate. When shutdown is initiated, the RPC server is stopped
means it will stop handling the new request, which is ok, but at the same
time it will stop the communication needed for the in-progress operations. For
example, if live migration is in progress, the source and destination compute
communicate (sync and async way) multiple times with each other. Once the RPC
server on the compute service is stopped, it cannot communicate with the other
compute and fails the live migration. It will lead the system as well as the
instance to be in an unwanted or unrecoverable state

Use Cases
---------

As an operator, I want to be able to gracefully shut down (SIGTERM) the Nova
services so that it will not impact the users' in-progress operations or
keep resources in usable state.

As an operator, I want to be able to keep instances and other resources in a
usable state even if service is gracefully terminated (SIGTERM).

As an operator, I want to be able to take the actual benefits of the k8s pod
graceful shutdown when Nova services are running in k8s pods.

As a user, I want in-progress operations to be completed before the service
is gracefully terminated (SIGTERM).

Proposed change
===============

For detailed context, refer to the graceful shutdown `backlog spec`_.

Split the new and in-progress requests via RPC:
-----------------------------------------------

RPC communication is an important part of services to finish a particular
operation. During shutdown, we need to make sure we keep the required RPC
servers/buses up. If we stop the RPC communication, then it is nothing
different than service termination.

Nova implements, and this spec talks a lot about RPC server ``start``,
``stop``, and ``wait``, so let's cover them briefly from oslo.messaging/RPC
resources point of view, and to understand this proposal in an easy way.
Most of you might know this, so you can skip this section.

* RPC server:

  * creation and start():

    * It will create the required resources on oslo.messaging side, for
      example, dispatcher, consumer, listener, and queues.
    * It will handle the binding to the required exchanges.

  * stop():

    * It will disable the listener ability to pick up any new message
      from the queue, but will dispatch the already picked message to
      the dispatcher.
    * It will delete the consumer.
    * It will not delete the queues and exchange on the message broker side.
    * It will not stop RPC clients sending new messages to the queue, however,
      they will not be picked because the consumer and listener are stopped.
  * wait():

    * It will wait for the thread pool to finish dispatching all the already
      picked messages. Basically, this will make sure methods are called on the
      manager.

Analysis per services and the required proposed RPC design change:

* The services listed below communicate with other Nova services' RPC servers.
  Since they do not have their own RPC server, no change needed:

  * Nova API
  * Nova metadata API
  * nova-novncproxy
  * nova-serialproxy
  * nova-spicehtml5proxy

* Nova scheduler: No RPC change needed.

  * Requests handling:
    Nova scheduler service runs as multiple workers, each having its own RPC
    server, but all the Nova scheduler workers will listen to the same RPC
    topic and queue ``scheduler`` with fanout way.

    Currently, nova.service.py->stop() calls stop() and wait() on RPC server.
    Once RPC server is stopped, it will stop listening to any new messages.
    But it will not impact anything on the other scheduler workers, and they
    continue listening to the same queue and process the request. If any of
    the scheduler worker is stopped, then the other workers will process the
    request.

  * Response handling:
    Whenever there is a RPC call, oslo.messaging creates another reply queue
    connected with the unique message id. This reply queue will be used to
    send the RPC call response to the caller. Even if the RPC server is stopped
    on this worker, it will not impact the reply queue.

    We still need to keep the worker up until all the responses are sent via
    the reply queue, and for that, we need to implement the in-progress task
    tracking in scheduler services, but that will be handled in step 2.

  This way, stopping a Nova scheduler worker will not impact the RPC
  communication on the scheduler service.

* Nova conductor: No RPC change needed.

  The Nova conductor binary is a stateless service that can spawn multiple
  worker threads. Each instance of the Nova conductor has its own RPC server,
  but all the Nova conductor instances will listen to  the same RPC topic
  and queue ``conductor``. This allows the conductor instance to act as a
  distributed worker pool such that stopping an individual conductor instance
  will not impact the RPC communication for the pool of conductor instances,
  allowing other available workers to process the request. Each cell has its
  own pool of conductors meaning as long as one conductor is up for any given
  cell the RPC communication will continue to function even when one or more
  conductors are stopped.

  The request and response handling is done in the same way as mentioned for
  the scheduler.

  .. note::

     This spec does not cover the conductor single worker case. That might
     requires the RPC designing for conductor as well but it need more
     investigation.

* Nova compute: RPC design change needed

  * Request handling:
    The Nova compute runs as a single worker per host, and each compute per
    host has their own RPC server, listener, and separate queues. It handles
    the new request as well as the communication needed for in-progress
    operations on the same RPC server. To achieve the graceful shutdown, we
    need to separate communication for the new requests and in-progress
    operations. This will be done by adding a new RPC server in the compute
    service.

    For easy readability, we will be using a different term for each RPC
    server:

    * 'ops RPC server': This will be used for the new RPC server, which
      will be used to finish the in-progress requests and will stay up during
      shutdown.
    * 'new request RPC server': This will be used for the current RPC server,
      which is used for the new requests and will be stopped during shutdown.

  * 'new request RPC server' per compute:
    No change in this RPC server, but it will be used for all the new requests,
    so that we can stop it during shutdown and stop the new requests on the
    compute.

  * 'ops RPC server' per compute:

    * Each compute will have a new 'ops RPC server' which will listen to a new
      topic ``compute-ops.<host>``. ``compute-ops`` name is used because it
      is mainly for compute operations, but a better name can be used if
      needed.
    * It will use the same transport layer/bus and exchange that the
      'new request RPC server' uses.
    * It will create its own dispatcher, listener, and queue.
    * Both RPC server will be bound to the same endpoints (same compute
      manager), so that requests coming from either server are handled by
      the same compute manager.
    * This server will be mainly used for the compute-to-compute operations and
      server external events. The idea is to keep this RPC server up during
      shutdown so that the in-progress operations can be finished.
    * In shutdown, nova.service will wait for the compute to tell if they
      finished all their tasks, so that it can stop the 'ops RPC server' and
      finish the shutdown.

  * Response handling:
    Irrespective of request is coming from either RPC server, whenever there
    is a RPC call, oslo.messaging creates another reply queue connected with
    the unique message id. This reply queue will be used to send the RPC call
    response to the caller. Even RPC server is stopped on this worker, it
    will not impact the reply queue.

  * Compute service workflow:

    * SIGTERM signal is handled by oslo.service, it will call stop on
      nova.service
    * nova.service will stop the 'new request RPC server' so that no new
      requests are picked by the compute. The 'ops RPC server' is running and
      up.
    * nova.service will wait for the manager to signal once all in-progress
      operations are finished.
    * Once compute signal to nova.service, then it will stop the
      'ops RPC server' and proceed with service shutdown.

  * RPC client:

    * The RPC client stays as a singleton class, which is created with the
      topic  ``compute.<host>``, meaning that by default message will be
      sent via 'new request RPC server'.
    * If any RPC cast/call wants to send a message via the 'ops RPC server',
      they need to override the ``topic`` to ``compute-ops.<host>`` during
      client.prepare() call.
    * If the RPC client detects an old compute (based on version_cap), then it
      will fall back to send the message to the 'new request RPC server' topic
      ``compute.<host>``.
    * Which RPC cast/call will be using the 'ops RPC server' will be decided
      during implementation, so that we can have a better judgment on what all
      methods are used for the operations we want to finish during shutdown.
      A draft list where we can use the 'ops RPC server':

      .. note::

         This is draft list and can be changed during implementation.

      * Migrations:

        - Live migration:

          .. note::

             We will be using the 'new request RPC server' for
             check_can_live_migrate_destination and
             check_can_live_migrate_source methods, as this is the very initial
             phase where the compute service has not started the live
             migration. If shutdown is initiated before live migration request,
             came then migration should be rejected.

          - pre_live_migration()
          - live_migration()
          - prep_snapshot_based_resize_at_dest()
          - remove_volume_connection()
          - post_live_migration_at_destination()
          - rollback_live_migration_at_destination()
          - drop_move_claim_at_destination()

        - resize methods
        - cold migration methods

      * Server external event
      * Rebuild instance
      * validate_console_port()
        This is when the console is already requested, and if port validation
        request is going on, the compute should finish it before shutdown so
        that users can get their requested console.

* Time based waiting for services to finish the in-progress operations:

  .. note::

     The time based waiting is a temporary solution. Later, it will be
     replaced by the proper tracking of in-progress tasks.

  * To make the graceful shutdown less complicated, this spec proposes a
    configurable time-based waiting for services to complete their operations.
  * The wait time should be less than global graceful shutdown timeout. So that
    external system or oslo.service does not shut down the service before the
    service wait time is over.

* Some specific examples of the shutdown issues which will be solved by this
  proposal:

  * Migrations:

    * Migration operations will use the 'ops RPC server'.

      * If migration is in-progress then the service shutdown will not
        terminate the migration; instead will be able to wait for the migration
        to complete.
      * Later, we will make long running migration to abort but that is out of
        scope from this spec.

    * Instance boot:

      * Instance boot operations will continue to use the
        'new request RPC server'. Otherwise, we will not be able to stop the
        new requests.
      * If instance boot requests are in progress by compute services, then
        shutdown will wait for compute to boot them successfully.
      * The instance external event will be received during graceful shutdown;
        therefore, an instance boot request will not be blocked for the
        external event.
      * If a new instance boot request arrives after the shutdown is initiated,
        then it will stay in the queue, and the compute will handle it once it
        is started again.
    * Any operations which is reached to compute will be completed before the
      service is shut down.

.. note::

   As per testing till now (eventlet mode), it does not require any change in
   oslo.messaging but we need to test it by running compute in native thread
   mode (with oslo.service threading backend ).

Graceful Shutdown Timeouts:
---------------------------

* Nova service timeout:

  We need two configurable timeouts in Nova:

  #. Overall Shutdown Timeouts:

     * The oslo.service already has the timeout (graceful_shutdown_timeout_)
       which is configurable per service and used to timeout the SIGTERM
       signal handler.
     * The oslo.service will terminate the Nova service based on
       graceful_shutdown_timeout_, even if the Nova service graceful shutdown
       is not finished.
     * Its default value is 60 seconds, which is less for Nova services. The
       proposal is to override its default value to 180 sec for all the
       Nova services.
     * The operator can override this value per Nova services.

  #. Timeout for Nova service to finish the in-progress tasks:

     * When shutdown is initiated, each service needs to finish its
       in-progress tasks, which can take time, and we have to timeout that
       before oslo.service graceful_shutdown_timeout_ reached.
     * We need this timeout because after finishing the in-progress tasks,
       Nova services need to call cleanup_host() on the manager, which also
       need some time to finish. If we do not have this timeout and service
       takes more time to finish in-progress tasks, then oslo.service
       graceful_shutdown_timeout_ will not let cleanup_host() to be executed.
     * We need to add this configurable timeout option per the Nova services
       and their default value should be lower than graceful_shutdown_timeout_,

* External system timeout:

  Depending on how Nova services are deployed, there might be an external
  system (for example, Nova running on k8s pods) timeout for graceful shutdown.
  That can impact the Nova graceful shutdown, so we need to document it
  clearly that if there is external system timeout, then Nova service timeout
  graceful_shutdown_timeout_ should be set accordingly. The external
  system timeout should be higher than graceful_shutdown_timeout_,
  otherwise external system will timeout and will interrupt the Nova graceful
  shutdown.

Alternatives
------------

One alternative for the RPC redesign is to handle the two topics per RPC
server. This needs a good amount of changes in oslo.messaging framework as well
as driver implementations. The idea is to allow oslo.messaging Target to take
more than one topic (take topic as a list) and ask the driver to create
separate consumers, listeners, dispatchers, and queues for each topic. Create
each topic binding to the exchange. This also requires oslo.messaging to
provide a new way to let the RPC server unsubscribe from a particular topic
and continue listening on other topics. We also need to redesign how RPC server
stop() and wait() works for now. This is too complicated and almost
re-designing the oslo.messaging RPC concepts.

One more alternative is to track and stop sending the request from Nova api or
the scheduler service, but that will not be able to stop all the new requests
(compute to compute tasks) or let in-progress things to complete.

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

This should provide a positive impact on end users so that the shutdown will
not stop their in-progress operations.

Performance Impact
------------------

No impact on normal operations, but the service shutdown will take more time.
There is a configurable timeout to control the service shutdown wait time.

Other deployer impact
---------------------

None other than a longer shutdown process, but they can configurable an
appropriate timeout for service shutdown.

Developer impact
----------------

None

Upgrade impact
--------------

Adding a new RPC server will impact the upgrade. The old compute will not have
the new 'ops RPC server' listening on topic RPC_TOPIC_OPS, so we need to handle
it with RPC versioning. If the RPC client detects an old compute (based on
version_cap), then it will fall back to send the message to the original RPC
server (listening to ``compute.<host>``); and therefore graceful shutdown will
not work on new compute nodes until all the computes are upgraded and the RPC
version_cap is removed.

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

* Implement the 'ops RPC server' on the compute service
* Use the 'ops RPC server' for the operations we need to finish during
  shutdown, for example, compute-to-compute tasks and server external events.
* RPC versioning due to upgrade impact.

Dependencies
============

* Eventlet removal for all Nova services:
  We need to make sure that graceful shutdown works fine on native threading
  mode, so we need to wait until all compute services are moved to the native
  threading mode. That will test the oslo.service with threading backend.
* oslo.service threading backend needs to consider the configurable
  graceful_shutdown_timeout_.

Testing
=======

* We cannot write tempest tests for this because tempest will not be able to
  stop the services.
* We can try (with some heavy live migration which will takes time) some
  testing in 'post-run' phase like it is done for evacuate tests.
* Unit and functional tests will be added.


Documentation Impact
====================

Graceful shutdown working will be documented along with other considerations,
for example, timeout or wait time considered for the graceful shutdown.

References
==========

* PoC:

  * Code change: https://review.opendev.org/c/openstack/nova/+/967261
  * PoC results: https://docs.google.com/document/d/1wd_VSw4fBYCXgyh5qwnjvjticNa8AnghzRmRH3H8pu4/

* PTG discussions:

  * https://etherpad.opendev.org/p/nova-2026.1-ptg#L860
  * https://etherpad.opendev.org/p/nova-2025.1-ptg#L413
  * https://etherpad.opendev.org/p/r.3d37f484b24bb0415983f345582508f7#L180

.. _`websockify.websocketproxy`: https://github.com/novnc/websockify/blob/e9bd68cbb81ab9b0c4ee5fa7a62faba824a142d1/websockify/websocketproxy.py#L300
.. _`websockify`: https://github.com/novnc/websockify
.. _`start_service`: https://github.com/novnc/websockify/blob/e9bd68cbb81ab9b0c4ee5fa7a62faba824a142d1/websockify/websockifyserver.py#L861
.. _`new_websocket_client`: https://github.com/openstack/nova/blob/23b462d77df1a1d09c43d0918bca853ef3af1e3f/nova/console/websocketproxy.py#L164C9-L164C29
.. _`close_connection`: https://github.com/openstack/nova/blob/23b462d77df1a1d09c43d0918bca853ef3af1e3f/nova/console/websocketproxy.py#L150
.. _`graceful_shutdown_timeout`: https://github.com/openstack/oslo.service/blob/8969233a0a45dad06c445fdf4a66920bd5f3eef0/oslo_service/_options.py#L60
.. _`backlog spec`: https://specs.openstack.org/openstack/nova-specs/specs/backlog/approved/nova-services-graceful-shutdown.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2026.1 Gazpacho
     - Introduced
