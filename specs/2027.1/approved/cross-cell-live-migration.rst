..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Cross-Cell Live Migration
=========================

https://blueprints.launchpad.net/nova/+spec/cross-cell-live-migration

Cells have been a native part of Nova for years now, yet live migration between
cells is still not implemented. In order to allow for more adoption of multiple
cells and to reduce the feature delta between deployment choices, we should
close the gap and fix this.


Problem description
===================

Nova does not allow for live migration between cells. While cold migration
(and thus resize) *is* supported, such operations are not ideal for operators
performing maintenance and upgrades because they are disruptive to the
workloads in the instances. Further, the live migration operation has become
quite fragmented and disorganized over the years as new technologies and
approaches have been bolted on, fixes and cleanups inserted into various
places to address issues, etc.

Use Cases
---------

As an operator I want to split my deployment into multiple cells for the
increased scale and performance I gain by doing so, without losing the
ability to migrate workloads around during maintenance operations.

As a user, I want my operator to be able to perform host-level maintenance or
even cell-by-cell upgrades without having to force my instance to restart for
a cold migration.

Proposed change
===============

Currently, live migration involves multiple back-and-forth communication steps
between the source and destination nodes. For computes in different cells, this
is not possible since they do not sit on the same MQ bus and do not share a
common database (both by design). Some have argued in the past that compute
nodes should not have to communicate thusly as a matter of principle for
isolation (security-wise and upgrade-wise) and this is another argument in
favor of moving away from that design.

Currently, conductor is positioned as a mediator for operations such as this,
but in the case of live migration it is *mostly* just involved in kicking off
the process. Moving the orchestration between the computes from the source
compute to the (super) conductor allows us to effect a complex cross-cell live
migration without the computes needing to comunicate (aside from the obvious
communication of the actual live migration stream between the libvirt/qemu
components on each node). The compute nodes will avoid RPC communication
regardless of if a cross-cell migration is happening or not for consistency.

This spec proposes a new API operation (called `liveMigrate` for the
moment), a new conductor task, and new compute RPC plumbing that implement the
above goals. Much of the internals will be re-used but with new RPC calls that
carry different pre/post condition expectations. This new operation will be
an eventual replacement for the current live migration operation, not simply
an alternative when cross-cell behaviors are desired.

The new process will be implemented in conductor as a new task class, peer to
the existing ``LiveMigrateTask``, but modeled after the cross-cell cold
migration task that currently exists. The pre-creation and copying of instance
records will be important to mirror (code reused where possible) for the new
operation if and when the migration will cross cells.

In the future where we are ready to remove the v1 migration plumbing, we may
decide to treat it like virt/network driver removals in the past, or we could
consider hooking up the v2 plumbing in a way that allows "as compatible as
possible" behavior to be honored through the old API. That decision can be
deferred to that point.

New API operation
-----------------

Because the existing live migration operation has multiple legacy modes of
operation, carries with it a lot of technical debt, but is also a critical and
well-understood operation, we propose a new API operation be created. This will
have a defined API and behavior, will drive the new flow when called and will
leave the existing flow alone.

Benefits:
 - Avoids disturbing the existing live migration code and allows it to remain a
   viable alternative until the new operation is trusted
 - Avoids needing to maintain compatibility with the existing flow, further
   complicating the existing code and allowing the new code to rethink some
   things.
 - Provides us a path to ultimately deprecate and "remove" the old mechanism
   (like we have done when dropping virt drivers, network models, etc)

Drawbacks:
 - Adds a new API, requiries some handling in the client, users will need to
   know the differences
 - Duplicated code for some time to come (although ultimately an opportunity to
   remove more in the long run)

The new API will inherit the semantics of the current latest microversion
``os-migrateLive`` action. Specifically:

 - An optional ``host`` parameter is accepted, and if provided, the scheduler
   will be consulted to make sure the host is suitable
 - The `block_migration` parameter is not accepted and the behavior of ``auto``
   will be assumed.
 - The ``disk_over_commit`` parameter is not accepted
 - A new optional parameter of ``availability_zone`` will be accepted which, if
   present, will be used to scope the scheduling to only hosts within that AZ.
   If ``host`` is also provided, the operation will fail if the specified host
   is not in the specified AZ.
 - The async behavior of 2.34 and later will be assumed.

An instance that has a ``pinned_availability_zone`` cannot be migrated to a
different ``availability_zone``. Such a request will be rejected. An
operator must first remove the existing pin before migrating the instance to a
different availability zone. This avoids retaining a stale pin after the
instance has moved, which could incorrectly constrain scheduling for later
operations such as resize or evacuation. Note that this behavior is consistent
with live migration v1 today:

 1. Choosing a host not in the chosen (or currently-pinned) AZ will result in
    a scheduling failure
 2. The instance must be unpinned before migrating to another AZ

Just like with v1 live migration, even excluding the potential for crossing
cells, we cannot re-pin an instance to an AZ following the live migration
operation because the computes have no ability to update the request spec
(where the pin is held) after successful completion. This differs from
operations such as resize or cold migration as the former can take a very long
time to run, will be completed or reverted sometime in the future by a
separate API request, and it is not feasible to have a superconductor thread
wait for the duration. Unshelve to an AZ will re-pin an instance to the new
one, but does not revert that pin if the unshelve fails (which happens async
on the compute node) but this is acceptable since the instance is not running
and is not auto-reverted back to a source node (in a potentially-different AZ)
on failure. Live migration, however, does have a running instance that will
(and must) be reverted back to the source node if the operation fails.

An additional policy rule will be added to control whether or not a user is
allowed to push a migration across cell boundaries. This will mirror the
`compute:servers:resize:cross_cell` policy knob we have for cold migration.
Since live migration (unlike cold migration and resize) is an admin/
manager-only operation, this extra knob will initially default to the same
value as for live migration itself.

.. note:: Features will not be added to the v1 migration path without same-
  microversion parity in the v2 path. This ensures that we do not create a
  diverging feature delta whereby the old migration operation is the only way
  to access a feature added after the new operation exists.

Ownership of the process
------------------------

Right now, the source compute node basically owns the entire migration process.
The new process will continue to make the compute nodes own as much as
possible, but with a different distribution and with conductor doing more of
the coordination ahead of time.

In the new mode, the conductor will be responsible for collecting information
from the compute nodes (the check phases) as it can talk to both. It will
also be responsible for pre-creating the instance records in the destination
database and setting up the cell routing for the new instance (more on that
later). It will perform the equivalent of the "pre_live_migration" operation
today, which informs the receiving compute node of the pending operation and
then will kick off the actual migration with the source node.

For a cross-cell migration, the conductor will create the destination instance
with ``hidden`` set, together with the instance's block device mappings,
virtual interfaces, tags, instance actions, and migration records. The
destination instance remains hidden until the destination compute has
confirmed the migration completed. If the migration is rolled back, the
destination records will be hard-deleted.

It should be noted that an important aspect of the design here is that the
conductor task thread does not persist through the duration of the migration
operation. A naive approach with such a long-running task seems advantageous,
in that the conductor retains the ability to perform cross-cell cleanup (in
both success and failure scenarios). However, in practice live migrations of
real workloads can take hours to complete. Having a headless conductor thread
running for the duration, monitoring the process via RPC call polling or
long-call mechanics, unable to be addressed for an abort or force-complete
operation would be very fragile. Further, increasing the number of nodes that
must survive until the end for success by 50% subsantially increases the risk
that an errant operator action, k8s restart, or simply a network outage would
compromise the operation. Thus, the proposal here does not increase the number
and scope of nodes that are involved in the critical part of operation, it
simply rebalances the responsibilities and expectations between the
source and destination.

The destination compute node will take a more active role in the migration in
the new flow, by starting an actual monitor thread when the conductor informs
it to expect an incoming migration. Today we already "record" that a task is
started so that we can avoid shutting down until a pending migration has
completed. In the new flow this will start an actual thread that will monitor
for the incoming migrated virtual machine, and finish the process once it is
completed. It will be able to monitor global information like placement
allocations, as well as local information such as the presence of a matching
libvirt virtual machine. It will also need to determine when a migration has
been aborted and do cleanup. It may determine a migration has failed because
placement allocations have been reverted, or because it saw a libvirt virtual
machine appear and then disappear, etc. Local node cleanup when failure/abort
has been determined will be done, and the source node will (as described below)
handle global resource revert/cleanup. Initially we will consider the placement
allocation confirm/revert to be the definitive trigger for success/failure
as viewed by the destination node.

The source compute node will be responsible for starting the migration, doing
the time-sensitive task of activating the port bindings for the destination
node, cleaning up placement allocations, and its own local node cleanup. On
failure, it will do the global rollback operations necessary for network and
volume setup, revert the placement allocations, etc within the scope of what it
*can* do. Finalizing the cell routing information is not something the source
node *can* do, and is described below.

The source and destination nodes will be responsible for hard-deleting the
instance (and related) records from the database depending on success (delete
from source) or failure (delete from dest) *if* the migration is crossing a
cell boundary. Information about this will need to be communicated to the nodes
by conductor ahead of time.

It's important to clearly define each finalization step (both for successful
completion and failure/rollback), and which of the compute nodes will own it.

We also acknowledge that live migration currently has a variety of difficult
race conditions surrounding exceptional scenarios like deleting migrating
instances, handling expected and unexpected compute service interruptions, etc.
While we aim to do a better job of handling those in this effort (aided in
part by the graceful shutdown work), fixing all of them in the first revision
is both impractical and unlikely. Calling them out when we know about them and
addressing them along with the ones we will inevitably find in the field is
expected future work.

Finalizing the process
----------------------

After a migration there is an important final step required that neither the
source nor destination compute nodes can perform: updating the cell routing
information (i.e. the InstanceMapping). In order to avoid a conductor thread
being required to fix up this routing information after the (potentially
hours-long) live migration has completed, we propose a lazy approach that will
maintain access to the instance regardless of when and how a migration
completed.

Currently, an instance may have only a single ``InstanceMapping`` record in the
database and thus only one cell affiliation, because it may only be in one cell
at a time. We propose to add a new field called ``old_cell_id`` to
``InstanceMapping``. This will indicate to the API (et al) that the instance
*may* be in either the "old" cell or the "new" cell right now. During setup,
the conductor will mutate the ``InstanceMapping`` to set ``old_cell_id`` to
reflect the cell the instance is currently in and the ``cell_id`` to reflect
the new cell we expect the instance to migrate into. When the API goes to look
up an instance (and thus resolves its cell) it will recognize the fact that it
could be in either. It will first try looking up the cell in the "old" cell,
and if present, will continue as if that is the case. If it hits a `NotFound`
there, it will try again but in the "new" cell. Assuming it finds it, it will
update the ``InstanceMapping`` to ``NULL`` out the ``old_cell_id`` and
continue, knowing the migration has completed.

In order for this to work, all of the finalization work must be done by the
compute nodes (both for normal completion and the revert/rollback case) so
that the only final resolution required is to flip the mapping. The API can
do that lazily for either outcome, depending on which cell the instance
record remains in once it is deleted from the cell it did not remain in.

In the case where either cell is down and the instance mapping remains
ambiguous, we need to mirror the "down cell" behavior for fetching an
instance. This would only be the case if the target cell reports lack of
completion (i.e. instance is still `hidden=True`) and the source cell does not
respond or if the source cell reports completion (instance is deleted) and
the target cell does not respond.

VIF plug events
---------------

Currently the source compute waits for the VIF plug events that are triggered
by neutron when we make the ``pre_live_migration`` call to the destination.
Since the source compute will not do that itself, it can't wait for them in
a deterministic way.

Going forward, migrations that are initiated with this new API will have
instance events sent (i.e. copied) to both source and destination nodes during
the migration, allowing for proper waiting on either side. The compute manager
will already ignore events that arrive without a waiter, so no change is
required on the receiving end for this.

Host selection
--------------

When selecting a new host for an otherwise unconstrained live migration using
the new operation, we will rely on the existing `Cross cell weigher`_ that
favors same-cell hosts over hosts in other cells.

Parallel effort: consumer types for migration allocations
---------------------------------------------------------

Placement allows us to set a ``consumer_type`` on an allocation to indicate
the owner/purpose of those allocations. Although not a strict dependency of
this work, doing so will provide additional visibility into the purpose (and
significance) of the migration allocations that we already make to reserve
rollback resources on the source. Since we will now be dependent on those to
signal the confirm/revert behavior, setting the ``consumer_type`` will help
increase visibility. Further, we could propose a feature in placement that
requires ``service_role`` (or some other authorization) to delete allocations
with ``consumer_type='COMPUTE_MIGRATION'`` in the future. This hazard will
at least be documented in nova, and potentially highlighted by the openstack
client as dangerous as an interim measure before actual policy-based rejection
is available in placement.

Because this change isn't a direct dependency of this work, it will be kept
separate from the serialized stack of changes for the v2 operation and can
be reviewed, discussed, and landed independently. Adding the consumer types to
allocations is proposed in `Consumer types for allocations`_.

Known issue: instance names
---------------------------

There is a quirk in nova where we maintain and enforce the insance name in
libvirt, which by default is based on a configurable format that includes the
database id. Since instances in adjacent cells will have overlapping ``id``
fields, we must avoid collisions in some way as during migration the instance
could land on a compute node that already has an instance with the same name.

Ideally we would migrate away from this unsafe publication of private/internal
IDs (as we have previously identified we should do). For greenfield deployments
this is easier, but for existing ones it is harder. Ideally we should move to a
stable and actually-unique format of ``instance-$UUID`` and deprecate the
ability to control the name via config. For existing domains, we can rename
them at hard reboot time, and we should probably start doing this sooner than
later.

During live migration, we are not allowed to simply generate a new name in the
destination XML. However, the ``virsh`` command for live migration does have a
way to specify a new destination name, which probably means there is some way
for us to effect such a change in our own migration. If that is not possible
for some reason then we may need to simply require operators to hard reboot
their instances before they can be migrated across cells (or accept that the
migration may fail due to a name conflict).

We will document that in order for this to work, you must have changed your
instance name template to something database-independent. Simultaneously, we
will make that easier by fixing our default and making live migration address
changes for running instances in `Instance name template migration`_

Alternatives
------------

An alternative to the entire approach here is to pass a ``CellMapping`` object
down to the source compute (or conductor) to perform the migration much as it
is today but with the ability to contact the other node directly. Arguments
against this are:

#. The cell services know nothing about cells today and this would require
   a major change in that area.
#. The compute (or conductor) would have to pre-create the instance, which is
   something it does not currently do today. Similarly, they assume they are
   reading the same instance out of the database today, but this scenario would
   have them subtly not doing that.
#. Both the source and destination nodes would need to have the ``CellMapping``
   for the duration of the operation.
#. It would tie the cells together a bit too much for a period of time, both in
   terms of dependencies but also potentially in requiring a change to firewall
   rules and ACLs in RabbitMQ/mariadb which violate the goal of them being
   largely separate.

Another alternative would be to create an upcall relationship between conmpute
and superconductor (or cell and super conductors). This would be extremely
unfortunate and would basically cause every real deployment to have upcalls
enabled forever going forward. But it is technically an option.

It would also be possible to change the relationship of nova-compute to
nova-api such that we provide a new API for "internal events" or other
internal services. Such a mechanism could be used by the compute service to
signal things at the top-most layer, such as live migration completion. Today,
we never call our own API but that could potentially change. It would require
operators to provide network access between those services where there may be
none today, and would have upgrade implications both initially and over time
as we would start depending on that from the compute layer. This is both an
alternative for the placement signaling portion of this effort and something
we could leverage in the future, should it become available.

Data model impact
-----------------

The Instance object already has the ``hidden`` flag we need to be able to
pre-create it in the destination database that cross-cell cold migration uses.
However, ``MigrateData`` objects may need to change in order to convey
additional information between the computes. Further, we will need a change to
the ``InstanceMapping`` object and database schema to handle the dual-cell
routing feature.

REST API impact
---------------

A new server action called ``liveMigrate`` and new microversion to match.
The intent is to mirror the behavior of the current-revision ``os-migrateLive``
operation with the addition of the availability zone handling provided here.

.. code-block:: json

    {
        "liveMigrate": {
            "availability_zone": "zone2",
            "host": "myhost7"
        }
    }

Normal response code: ``202``

A ``400`` will be returned in the case of:
 - Invalid AZ or host provided
 - Host is not in requested AZ
 - Instance is pinned to a different AZ

Security impact
---------------

Network connectivity suitable for libvirt live migrations will remain the same
as it is today. Meaning, even though computes in different cells will not
communicate with each other over RPC, libvirt connectivity is required for
live migrations to be possible.

Notifications impact
--------------------

The new live migration process must make sure to send the same notifications as
the existing one (and provide equivalent instance action/event recording).

Other end user impact
---------------------

None.

Performance Impact
------------------

This will increase the number of RPC calls required for a live migration
operation.

Other deployer impact
---------------------

See the security discusson above regarding computes in adjacent cells needing
a viable path for network communication to facilitate a migration.

Developer impact
----------------

Additional efforts this cycle aim to add AZ targeting to the other move
operations. If those changes land before the API patch for this spec, then
all is well. If they do not, we will address the concern over adding or
removing the AZ targeting portion of the API change for this at that time.

Upgrade impact
--------------

The existing RPC pinning support should prevent us from being able to do this
new operation until both source and destination cells have been upgraded to
support it. Since that determination is made asynchronously after the API
call has returned, such a case would be perceived by the client as a 202 with
a subsequent failure (like any other failure in the precheck phase).

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Work Items
----------

These are high-level work items, which will ideally be split into smaller
patches as appropriate to contain refactoring separately from new functionality
and especially from version bumps.

#. Begin work on ``consumer_type='migration'`` support for our migration
   allocations (in parallel with the items below).
#. Make the ``InstanceMapping`` DB and object change
#. Make the external event dispatch capable of duplicating events to both
   source and destination hosts when a new migration is in progress.
#. Create the new REST API call and associated version bump and sample tests
   (this will be early in the series for easier testing but will move to the
   end before merge per convention). Stubbed out until the step below where it
   can be plumbed in.
#. Create a detailed plan for every pre and post operation that needs to happen
   for the successful and failure paths, identifying which node currently does
   it and which node will do it in the new plan. Identify which things need to
   happen quickly (such as activating port bindings), which things need to
   happen in a very specific order, and which things can happen
   slowly/later/async. Identify a clear deterministic way that both nodes can
   agree that a migration has succeeded or failed without coordinating
   directly over RPC to avoid cases where they think the other "won".
#. Identify re-usable pieces of existing compute node live migration process
   that may need to be split out into separate helpers to facilitate re-use
   between the old and new workflows.
#. Implement the compute RPC calls necessary for the new workflow, along with a
   compute RPC version bump and associated service version bump.
#. Implement the new task class in conductor that will orchestrate this modern
   workflow.
#. Survey the existing set of live migration functional tests (and regression
   tests) to make sure we cover all the relevant corner cases that have been
   patched up in recent years with v1. See the effort noted below.
#. Client and SDK changes to allow pushing the new operation.

Dependencies
============

None.

Testing
=======

Because this will be a new flow from REST API through conductor and to the
computes, the existing tests should be unaffected. New unit and functional
tests for all parts of the new flow will be added. The existing corpus of tests
for live migration will provide a roadmap for the new flow, and specifically
for test coverage of the new flow. In-tree tests for bugs and regressions that
have been fixed over the years as well as edge cases and complex failure modes
(and the resulting cleanup) will need to be examined carefully. Some of the
existing tests will cover cases not possible with the new flow, but many of the
situations and scenarios will apply, even if they must be tested in a different
way.

Tempest testing of the new operation will obviously be required and can
leverage the existing tests either directly or as a map for new tests to be
written.

Documentation Impact
====================

Operator/admin documentation of the new operation will be provided, explaining
why the operation exists, and adding the new api-ref details of course.

References
==========

.. _2027.1 PTG discussion: https://etherpad.opendev.org/p/nova-2027.1-ptg
.. _Placement consumer types spec: https://docs.openstack.org/placement/2025.2/specs/train/approved/2005473-support-consumer-types.html
.. _Cross cell weigher: https://github.com/openstack/nova/blob/master/nova/scheduler/weights/cross_cell.py
.. _Migrate a server to an availability zone spec: https://review.opendev.org/c/openstack/nova-specs/+/1013094
.. _Instance name template migration: https://review.opendev.org/q/topic:%22instance-name-template%22
.. _Consumer types for allocations: https://review.opendev.org/c/openstack/nova/+/1012083

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2027.1 Indri
     - Introduced
