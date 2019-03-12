..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================
Cross-cell resize
=================

https://blueprints.launchpad.net/nova/+spec/cross-cell-resize

Expand resize (cold migration) support across multiple cells.


Problem description
===================

Multi-cell support was added to the controller services (API, conductor,
scheduler) in the Pike release. However, server move operations, like resize,
are restricted to the cell in which the instance currently lives. Since
it is common for deployments to shard cells by hardware types, and therefore
flavors isolated to that hardware, the inability to resize across cells is
problematic when a deployment wants to move workloads off the old hardware
(flavors) and onto new hardware.

Use Cases
---------

As a large multi-cell deployment which shards cells by hardware generation,
I want to decommission old hardware in older cells and have new and existing
servers move to newer cells running newer hardware using newer flavors without
users having to destroy and recreate their workloads.

As a user, I want to my servers to retain their IPs, volumes and UUID
while being migrated to another cell.

Proposed change
===============

This is a complicated change, which the proof of concept patch [1]_ shows.
As such, I will break down this section into sub-sections to cover the various
aspects in what needs to be implemented and why.

Keep in mind that at a high level, this is mostly a large data migration from
one cell to another.

This spec attempts to provide a high level design based on prototypes using
both a shelve-based approach and, after initial spec review [2]_, an approach
modeled closer to the traditional resize flow. This version of the spec focuses
on the latter approach (without directly calling shelve methods). There will be
unforeseen issues that will arise during implementation so the spec tries to
not get into too low a level of implementation details and instead focuses on
the general steps needed and known issues. Open questions are called out
as necessary.

Why resize?
-----------

We are doing resize because cells can be sharded by flavors and resize is the
only non-admin way (by default) for users to opt into migrating from one cell
with an old flavor (gen1) to a new flavor (gen2) in a new cell.

Users, by naturally resizing their servers every once in a while, will help
with the migration. If not, the admins can also give them "new" flavors and
tell them they need to resize their servers by a certain date. By having this
be doable by a user-controlled process, the users can help with the migration
without knowing anything about cells underneath.

Terms
-----

Common terms used throughout the spec.

* Source cell: this is the cell in which the instance "lives" when the resize
  is initiated.

* Target cell: this is the cell in which the instance moves during a cross-cell
  resize.

* Resized instance: an instance with status ``VERIFY_RESIZE``.

* Super conductor: in a `split-MQ`_ deployment, the super conductor is running
  at the "top" and has access to the API database and thus can communicate with
  the cells over RPC and directly to the cell databases.

* Hard delete: most tables in the cell database schema, like ``instances``,
  use the `SoftDeleteMixin`_ which means when the corresponding object is
  destroyed, the record's ``deleted`` column is updated to a non-0 value which
  takes it out of most queries by default, like when listing servers in the
  API. This is commonly referred to as a "soft delete" of the record since it
  is still in the table and will not be actually deleted until the
  ``nova-manage db archive_deleted_rows`` command is run. Note that this
  concept of a "soft deleted" record is not the same as a server with status
  ``SOFT_DELETED`` in the API, which is a server that is marked for deletion
  but has not yet been reaped by the nova-compute service. Hard deleting cell
  database records is necessary in a cross-cell resize to avoid
  DBDuplicateEntry failures due to unique constraint violations because of
  soft deleted records in a cell database to which an instance is being
  resized.

.. _split-MQ: https://docs.openstack.org/nova/latest/user/cellsv2-layout.html#multiple-cells
.. _SoftDeleteMixin: https://github.com/openstack/oslo.db/blob/4.45.0/oslo_db/sqlalchemy/models.py#L142

Assumptions
-----------

* There is a lack of connectivity, e.g. SSH access, between compute hosts in
  different cells on which regular resize relies.

* The image service (glance), persistent volume storage (cinder) and tenant
  networks (neutron) span cells.

Goals
-----

* Minimal changes to the overall resize flow as seen from both an external
  (API user, notification consumer) and internal (nova developer) perspective.

* Maintain the ability to easily rollback to the source cell in case the
  resize fails.

Policy rule
-----------

A new policy rule ``compute:servers:resize:cross_cell`` will be added. It will
default to ``!`` which means no users are allowed. This is both backward
compatible and flexible so that operators can determine which users in their
cloud are allowed to perform a cross-cell resize. For example, it probably
makes sense for operators to allow only system-level admins or test engineers
to perform a cross-cell resize initially.

Resize flow
-----------

This describes the flow of a resize up until the point that the server
goes to ``VERIFY_RESIZE`` status.

API
~~~

The API will check if the user is allowed, by the new policy rule, to perform
a cross-cell resize *and* if the ``nova-compute`` service on the source host
is new enough to support the cross-cell resize flow. If so, the API will
modify the RequestSpec to tell the scheduler to not restrict hosts to the
source cell, but the source cell will be "preferred" by default.

There are two major reasons why we perform this check in the API:

1. The `2.56 microversion`_ allows users with the admin role to specify a
   target host during a cold migration. Currently, the API validates that the
   `target host exists`_ which will only work for hosts in the same cell in
   which the instance lives (because the request context is targeted to that
   cell). If the request is allowed to perform a cross-cell resize then we
   will adjust the target host check to allow for other cells as well.

2. Currently, the resize/migrate API actions are synchronous until conductor
   RPC casts to ``prep_resize()`` on the selected target host. This could be
   problematic during a cross-cell resize if the conductor needs to validate
   potential target hosts since the REST API response could timeout. Until the
   `2.34 microversion`_, the live migrate API had the same problem.
   If the request is allowed to perform a cross-cell resize then we will RPC
   cast from API to conductor.

.. _2.56 microversion: https://docs.openstack.org/nova/latest/reference/api-microversion-history.html#id51
.. _target host exists: https://github.com/openstack/nova/blob/c295e395d/nova/compute/api.py#L3570
.. _2.34 microversion: https://docs.openstack.org/nova/latest/reference/api-microversion-history.html#id31

Scheduler
~~~~~~~~~

A new ``CrossCellWeigher`` will be introduced which will prefer hosts from the
source cell by default. A configurable multiplier will be added to control the
weight in case an operator wants to prefer cross cell migrations. This weigher
will be a noop for all non-cross-cell move operations.

Note that once the scheduler picks a primary selected host, all alternate hosts
come from the `same cell`_.

.. _same cell: https://github.com/openstack/nova/blob/c295e395d/nova/scheduler/filter_scheduler.py#L399

(Super)Conductor
~~~~~~~~~~~~~~~~

The role of conductor will be to synchronously orchestrate the resize between
the two cells. Given the assumption that computes in different cells do not
have SSH access to each other, the traditional resize flow of transferring
disks over SSH will not work.

The ``MigrationTask`` will check the selected destinations from the scheduler
to see if they are in another cell and if so, call off to a new set of
conductor tasks to orchestrate the cross-cell resize. Conductor will set
``Migration.cross_cell_move=True`` which will be used in the API to control
confirm/revert logic.

A new ``CrossCellMigrationTask`` will orchestrate the following sub-tasks which
are meant to mimic the traditional resize flow and will leverage new compute
service methods.

**Target DB Setup**

Before we can perform any checks in the destination host, we have to first
populate the target cell database with the instance and its related data, e.g.
block device mappings, network info cache, instance actions, etc.

.. note:: After this point, if anything fails the conductor task will hard
          delete the instance and its related records from the target cell DB
          so the resize can be attempted again once the issue is resolved in
          the target cell.

In order to hide the target cell instance from the API when listing servers,
the instance in the target cell will be created with a ``hidden=True`` field
which will be used to filter out these types of instances from the API.
Remember that at this point, the instance mapping in the API points at the
source cell, so ``GET /servers/{server_id}`` would still only show details
about the instance in the source cell. We use the new ``hidden`` field to
prevent leaking out the wrong instance to ``GET /servers/detail``. We may also
do this for the related ``migrations`` table record to avoid returning multiple
instances of the same migration record to ``GET /os-migrations``
(coincidentally the ``migrations`` table already has an unused ``hidden``
column).

**Prep Resize at Dest**

Conductor will make a synchronous RPC call (using ``long_rpc_timeout``) to a
new method ``prep_snapshot_based_resize_at_dest`` on the dest compute service
which will:

* Call ``ResourceTracker.resize_claim()`` on the potential dest host in the
  target cell to claim resources prior to starting the resize. Note that
  VCPU, MEMORY_MB and DISK_GB resources will actually be claimed (allocated)
  via placement during scheduling, but we need to make the ``resize_claim()``
  for NUMA/PCI resources which are not yet modeled in placement, and in order
  to create the ``MigrationContext`` record.

* Verify the selected target host to ensure ports and volumes will work.
  This validation will include creating port bindings on the target host
  and ensuring volume attachments can be connected to the host.

If either of these steps fail, the target host will be rejected. At that point,
the conductor task will loop through alternate hosts looking for one that
works. If the migration fails at this point (runs out of hosts), then the
migration status changes to ``error`` and the instance status goes back to
its previous state (either ``ACTIVE`` or ``ERROR``).

Copy the ``instance.migration_context`` from the target DB to the source DB.
This is necessary for the API to route ``network-vif-plugged`` events later
when spawning the guest in the target cell.

**Prep Resize at Source**

Conductor will make a synchronous RPC call (using ``long_rpc_timeout``) to a
new method ``prep_snapshot_based_resize_at_source`` on the source compute
service which will behave very similar to how shelve works, but also coincides
with how the ``resize_instance`` method works during a traditional resize:

* Power off the instance.

* For non-volume-backed instances, create and upload a snapshot image of the
  root disk. Like shelve, this snapshot image will be used temporarily during
  the resize and upon successful completion will be deleted. The old/new
  image_ref will be stored in the migration_context.

* Destroy the guest on the hypervisor but retain disks, i.e. call
  ``self.driver.destroy(..., destroy_disks=False)``. This is necessary to
  disconnect volumes and unplug VIFs from the source host, and is actually
  very similar to the ``migrate_disk_and_power_off`` method called on the
  source host during a normal resize. Note that we do not free up tracked
  resources on the source host at this point nor change the instance host/node
  values in the database in case we revert or need to recover from a failed
  migration.

* Delete old volume attachments and update the BlockDeviceMapping records
  with new placeholder volume attachments which will be used on the dest host.

* Open question: at this point we may want to activate port bindings for the
  dest host, but that may not be necessary (that is not done as part of
  ``resize_instance`` on the source host during traditional resize today).
  If the ports are bound to the dest host and the migration fails, trying to
  recover the instance in the source cell via rebuild may not work (see
  `bug 1659062`_) so maybe port binding should be delayed, or we have to be
  careful about rolling those back to the source host.

.. _bug 1659062: https://bugs.launchpad.net/nova/+bug/1659062

If the migration fails at this point, any snapshot image created should be
deleted. Recovering the guest on the source host should be as simple as
hard rebooting the server (which is allowed with servers in ``ERROR`` status).

**Finish Resize at Dest**

At this point we are going to switch over to the dest host in the target cell
so we need to make sure any DB updates required from the source cell to the
target cell are made, for example, task_state, power_state, availability_zone
values, instance action events, etc

Conductor will make a synchronous RPC call (using ``long_rpc_timeout``) to a
new method ``finish_snapshot_based_resize_at_dest`` on the dest compute service
which will behave very similar to how unshelve works, but also coincides with
how the ``finish_resize`` method works during a traditional resize:

* Apply the migration context and update the instance record for the new
  flavor and host/node information.

* Update port bindings / PCI mappings for the dest host.

* Prepare block devices (attach volumes).

* Spawn the guest on the hypervisor which will connect volumes and plug VIFs.
  The new flavor will be used and if a snapshot image was previously created
  for a non-volume-backed instance, that image will be used for the root disk.
  At this point, the virt driver should wait for the ``network-vif-plugged``
  event to be routed from the API before continuing.

* Delete the temporary snapshot image (if one was created). This is similar to
  how unshelve works where the shelved snapshot image is deleted. At this point
  deleting the snapshot image is OK since the guest is spawned on the dest host
  and in the event of a revert or recovery needed on the source, the source
  disk is still on the source host.

* Mark the instance as resized.

Back in conductor, we need to:

* Mark the target cell instance record as ``hidden=False`` so it will show
  up when listing servers. Note that because of how the `API filters`_
  duplicate instance records, even if the user is listing servers at this exact
  moment only one copy of the instance will be returned.

* Update the instance mapping to point at the target cell. This is so that
  the confirm/revert actions will be performed on the resized instance in the
  target cell rather than the destroyed guest in the source cell.
  Note that we could do this before finishing the resize on the dest host, but
  it makes sense to defer this until the instance is successfully resized
  in the dest host because if that fails, we want to be able to rebuild in the
  source cell to recover the instance.

* Mark the source cell instance record as ``hidden=True`` to hide it from the
  user when listing servers.

.. _API filters: https://github.com/openstack/nova/blob/c295e395d/nova/compute/api.py#L2684

Confirm flow
------------

When confirming a resized server, if the ``Migration.cross_cell_move`` value
is True, the API will:

* RPC call to the source compute to cleanup disks
  similar to the ``driver.confirm_migration`` method and drop the move claim
  (free up tracked resource usage for the source node).

* Delete migration-based resource allocations against the source compute node
  resource provider (this can happen in the source compute or the API).

* Hard delete the instance and its related records from the source cell
  database.

* Update the ``Migration.status`` to ``confirmed`` in the target cell DB.

* Drop the migration context on the instance in the target cell DB.

* Change the instance vm_state to ``ACTIVE`` or ``STOPPED`` based on its
  current power_state in the target cell DB (the user may have manually powered
  on the guest to verify it before confirming the resize).

Revert flow
-----------

Similar to the confirm flow, a cross-cell revert resize will be identified
via the ``Migration.cross_cell_move`` field in the API. If True, the API will
RPC cast to a new conductor method ``revert_cross_cell_resize`` which will
execute a new ``CrossCellRevertResizeTask``. That task will:

* Update the instance and its related records in the source cell database
  based on the contents of the target cell database. This is especially
  important for things like:

  * BDMs because you can attach/detach volumes to/from a resized server.
  * The ``REVERT_RESIZE`` instance action record created by the API in the
    target cell. That is needed to track events during the revert in the
    source cell compute.

  Thankfully the API does not allow attaching/detaching ports or changing
  server tags on a resized server so we do not need to copy those back across
  to the source cell database.

* Mark the source cell DB instance as ``hidden=False`` to show it from the API
  while listing servers as we revert.

* Update the instance mapping to point at the source cell. This needs to happen
  before spawning in the source cell so that the ``network-vif-plugged``
  event from neutron is routed properly.

* Mark the target cell DB instance as ``hidden=True`` to hide it from the API
  while listing servers as we revert.

* RPC call the dest compute to terminate the instance (destroy the guest,
  disconnect volumes and ports, free up tracked resources).

* Hard delete the instance and its related records from the target cell
  database.

* Update the ``Migration.status`` to ``reverted`` in the source cell DB.

* RPC call the source compute to revert the migration context, apply the old
  flavor and original image, attach volumes and update port bindings, power on
  the guest (like in ``driver.finish_revert_migration``) and swap source node
  allocations held by the migration record in placement to the instance record.

  Note that an alternative to keeping the source disk during resize is to
  use the snapshot image during revert and just spawn from that (rather than
  power on from the retained disk). However, that means needing to potentially
  download the snapshot image back to the source host and ensure the snapshot
  image is cleaned up for both confirm and revert rather than just at the end
  of the resize. It would also complicate the ability to recover the guest
  on the source host by simply hard rebooting it in case the resize fails.

Limitations
-----------

1. The `_poll_unconfirmed_resizes`_ periodic task, which can be configured to
   automatically confirm pending resizes on the target host, will not support
   cross-cell resizes because doing so would require an up-call to the API to
   confirm the resize and cleanup the source cell database. Orchestrating
   automatic cross-cell resize confirm could be a new periodic task written in
   the conductor service as a future enhancement.

.. _\_poll_unconfirmed_resizes: https://github.com/openstack/nova/blob/c295e395d/nova/compute/manager.py#L7082

Known issues
------------

1. Rather than conductor making synchronous RPC calls during the resize with
   the ``long_rpc_timeout`` configuration option, a new option could be added
   specifically for cross-cell (snapshot-based) resize operations. Given a
   snapshot of a large disk could take a long time to upload (or download) it
   might be better to add new options for controlling those timeouts. For the
   initial version of this feature we will re-use ``long_rpc_timeout`` and we
   can add more granular options in the future if necessary.

2. One semantic difference in the API will be different events under the
   instance actions records during a resize, since the events are created via
   the ``wrap_instance_event`` decorator on the compute methods, and when using
   new methods with new names there will be new events compared to a normal
   resize. This could maybe be countered by passing a specific name to
   the decorator rather than just use the function name as it does today.
   Given there are no API guarantees about the events that show up under an
   action record, and this has always been internal details that leak out of
   the API, we will not try to overwrite the new function/event names, e.g.
   recording a ``compute_prep_resize`` event when calling the
   ``prep_snapshot_based_resize_at_dest`` method.

3. Servers created with personality files, commonly known as file injection,
   that are resized across cells will lose the personality files since they are
   not persisted in the database. There are two ways to view this. First is
   that a traditional resize will preserve a config drive with the personality
   files in it, so this would be a regression from that behavior since the
   config drive is going to get rebuilt on the destination host during a cross
   cell resize. On the other hand, servers with personality files that are
   resized today but do not have a config drive already lose their personality
   files during the migration because the files are not persisted and therefore
   even if they get metadata in the guest from the metadata API, they will not
   get the personality files used during server create (or the last rebuild).
   Similarly, servers that are evacuated, even if they had a config drive, will
   lose the personality files during the evacuation since the config drive is
   rebuilt on the destination host. It is also worth noting that the use of
   personality files `is deprecated`_.

.. _is deprecated: https://specs.openstack.org/openstack/nova-specs/specs/queens/implemented/deprecate-file-injection.html

Edge cases
----------

1. If the user deletes a server in ``VERIFY_RESIZE`` status, the API confirms
   the resize to clean up the source host before deleting the server from the
   dest host [3]_. This code will need to take into account a cross-cell resize
   and cleanup appropriately (cleanup the source host and delete records from
   the source cell).

2. When `routing network events`_ in the API, if the instance has a migration
   context it will lookup the migration record based on id rather than uuid
   which may be wrong if the migration context was created in a different cell
   database where the id primary key on the migration record is different.
   It is not clear if this will be a problem but it can be dealt with in a few
   ways:

   * Store the migration.uuid on the migration context and lookup the migration
     record using the uuid rather than the id.
   * When copying the migration context from the target cell DB to the source
     cell DB, update the ``MigrationContext.migration_id`` to match the
     ``Migration.id`` of the source cell migration record.

.. _personality-files:

3. It is possible to attach/detach volumes to/from a resized server. Because of
   this, mirroring those block device mapping changes from the target cell DB
   to the source cell DB during revert adds complication but it is
   manageable [4]_. The ability to do this to resized servers is not well
   known and arguably may not be officially supported to preserve any volumes
   attached during the revert, but because that is what works today we should
   try and support it for cross-cell resize.

.. _routing network events: https://github.com/openstack/nova/blob/c295e395d/nova/compute/api.py#L4883

Alternatives
------------

Lift and shift
~~~~~~~~~~~~~~

Users (or cloud operators) could force existing servers to be snapshot,
destroyed and then re-created from snapshot with a new flavor in a new cell.
It is assumed that deployments already have some kind of tooling like this for
moving resources across sites or regions. While normal resize is already
disruptive to running workloads, this alternative is especially problematic if
specific volumes and ports are attached, i.e. the IP(s) and server UUID would
change. In addition, it would require all multi-cell deployments to orchestrate
their own cross-cell migration tooling.

Shelve orchestration
~~~~~~~~~~~~~~~~~~~~

An alternative design to this spec is found in the PoC [1]_ and initial version
of this spec [2]_. That approach opted to try and re-use the existing
shelve and unshelve functions to:

* Snapshot and shelve offload out of the source cell.
* Unshelve from snapshot in the target cell.
* On revert, shelve offload from the target cell and then unshelve in the
  source cell.

The API, scheduler and database manipulation logic was similar *except* since
shelve was used, the instance was offloaded from the source cell which could
complicate getting the server *back* to the original source on revert and
require rescheduling to a different host in the source cell.

In addition, that approach resulted in new task states and notifications
related to shelve which would not be found in a normal resize, which could be
confusing, and complicated the logic in the shelve/unshelve code since it had
to deal with resize conditions.

Comparing what is proposed in this spec versus the shelve approach:

Pros:

- Arguably cleaner with new methods to control task states and notificiations;
  no complicated dual-purpose logic to shelve handling a resize, i.e. do not
  repeat the evacuate/rebuild debt.
- The source instance is mostly untouched which should make revert and
  recover simpler.

Cons:

- Lots of new code, some of which is heavily duplicated with shelve/unshelve.

Long-term it should be better to try for a hybrid approach (what is in this
spec) to have new compute methods to control notifications and task states to
closer match a traditional resize flow, but mix in shelve/unshelve style
operations, e.g. snapshot, guest destroy/spawn.

Data model impact
-----------------

* A ``cross_cell_move`` boolean column, which defaults to False, will be added
  to the ``migrations`` cell DB table and related versioned object.

* A ``hidden`` boolean column, which defaults to False, will be added to the
  ``instances`` cell DB table and related versioned object.

REST API impact
---------------

There will be no explicit request/response schema changes to the REST API.
Normal resize semantics like maintaining the same task state transition and
keeping the instance either ``ACTIVE`` or ``SHUTDOWN`` at the end will remain
intact.

While the instance is resized and contains records in both cells, the API will
have to take care to filter out duplicate instance and migration records while
listing those across cells (using the ``hidden`` field).

Security impact
---------------

As described in the `Policy rule`_ section, a new policy rule will be added
to control which users can perform a cross-cell resize.

Notifications impact
--------------------

Similar to task state transitions in the API, notifications should remain
the same as much as possible. For example, the *Prep Resize at Dest* phase
should emit the existing ``instance.resize_prep.start/end`` notifications.
The *Prep Resize at Source* phase should emit the existing
``instance.resize.start/end/error`` notifications.

The bigger impact will be to deployments that have a notification queue per
cell because the notifications will stop from one cell and start in another,
or be intermixed during the resize itself (prep at dest is in target cell while
prep at source is in source cell). It is not clear what impact this could have
on notification consumers like ceilometer though.

If desired, new versioned notifications (or fields to existing notifications)
could be added to denote a cross-cell resize is being performed, either as
part of this blueprint or as a future enhancement.

Other end user impact
---------------------

As mentioned above, instance action events and versioned notification behavior
may be different.

Performance Impact
------------------

Clearly a cross-cell resize will perform less well than a normal resize
given the database coordination involved and the need to snapshot an
image-backed instance out of the source cell and download the snapshot image
in the target cell.

Also, deployments which enable this feature may need to scale out their
conductor workers which will be doing a lot of the orchestration work
rather than inter-compute coordination like a normal resize. Similarly, the
``rpc_conn_pool_size`` may need to be increased because of the synchronous
RPC calls involved.

Other deployer impact
---------------------

Deployers will be able to control who can perform a cross-cell resize in
their cloud and also be able to tune parameters used during the resize,
like the RPC timeout.

Developer impact
----------------

A new ``can_connect_volume`` compute driver interface will be added with
the following signature::

  def can_connect_volume(self, context, connection_info, instance):

That will be used during the validation step to ensure volumes attached to
the instance can connect to the destination host in the target cell. The code
itself will be relatively minor and just involve parts of an existing volume
attach/detach operation for the driver.

Upgrade impact
--------------

There are three major upgrade considerations to support this feature.

* RPC: given the RPC interface changes to the compute and conductor services,
  those services will naturally need to be upgraded before a cross-cell resize
  can be performed.

* Cinder: because of the validation relying on volume attachments, cinder
  will need to be running at least Queens level code with the
  `3.44 microversion`_ available.

* Neutron: because of the validation relying on port bindings, neutron will
  need to be running at least Rocky level code with the
  ``Port Bindings Extended`` API extension enabled.

.. _3.44 microversion: https://docs.openstack.org/cinder/latest/contributor/api_microversion_history.html#id41


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Matt Riedemann <mriedem.os@gmail.com> (irc: mriedem)

Other contributors:
  None

Work Items
----------

At a high level this is the proposed series of changes that need to be made
in order, although realistically some of the control plane changes could be
made in any order as long as the cold migrate task change comes at the end.

* DB model changes (``migrations.cross_cell_move``, ``instances.hidden``).

* Various versioned objects changes for tracking a cross-cell move in
  the RequestSpec, looking up a Migration by UUID, creating InstanceAction
  and InstanceActionEvent records from existing data, etc.

* Scheduler changes to select destination hosts from multiple cells during
  a cross-cell move and weighing them so the "source" cell is preferred by
  default.

* Possible changes to the ``MigrationContext`` object for new fields like
  ``old_image_ref``, ``new_image_ref``, ``old_flavor``, ``new_flavor``,
  ``old_vm_state`` (this will depend on implementation).

* nova-compute RPC interface changes for the prep/validate at dest, prep
  at source, and finish resize at source operations.

* Adding new conductor tasks for orchestrating a cross-cell resize including
  reverting a resize.

* API plumbing changes to handle confirming/reverting a cross-cell resize.

* Add the new policy rule and make the existing resize flow use it to tell the
  scheduler whether or not target hosts can come from another cell, and if the
  target host is from another cell, to run the new cross-cell resize conductor
  task to orchestrate the resize rather than the traditional
  compute-orchestrated flow (where the source and target nova-compute services
  SSH and RPC between each other).


Dependencies
============

None


Testing
=======

The existing functional tests in the PoC change should give a good idea of
the types of wrinkles that need to be tested. Several obvious tests include:

* Resize both image-backed and volume-backed servers.

* Ensure allocations in the placement service, and resource reporting from
  the ``os-hypervisors`` API, are accurate at all points of the resize, i.e.
  while the server is in ``VERIFY_RESIZE`` status, after it is confirmed and
  reverted.

* Ensure volume attachments and port bindings are managed properly, i.e. no
  resources are leaked.

* Tags, both on the server and associated with virtual devices (volumes and
  ports) survive across the resize to the target cell.

* Volumes attached/detached to/from a server in ``VERIFY_RESIZE`` status are
  managed properly in the case of resize confirm/revert.

* During a resize, resources which span cells, like the server and its
  related migration, are not listed with duplicates out of the API.

* Perform a resize with at-capacity computes, meaning that when we revert
  we can only fit the instance with the old flavor back onto the source host
  in the source cell.

* Ensure start/end events/notifications are aligned with a normal same-cell
  resize.

* Resize from both an active and stopped server and assert the original
  status is retained after confirming and reverting the resize.

* Delete a resized server and assert resources and DB records are properly
  cleaned up from both the source and target cell.

* Test a failure scenario where the server is recovered via rebuild in the
  source cell.

Unit tests will be added for the various units of changes leading up to the
end of the series where the functional tests cover the integrated flows.
Negative/error/rollback scenarios will also be covered with unit tests and
functional tests as appropriate.

Since there are no direct API changes, Tempest testing does not really fit
this change. However, something we should really have, and arguably should
have had since Pike, is a multi-cell CI job. Details on how a multi-cell CI
job can be created though is unclear given the need for it to either
integrate with legacy devstack-gate tooling or, if possible, new zuul v3
tooling.


Documentation Impact
====================

The compute admin `resize guide`_ will be updated to document cross-cell
resize in detail from an operations perspective, including troubleshooting
and fault recovery details.

The compute `configuration guide`_ will be updated for the new policy rule
and any configuration options added.

The compute `server concepts guide`_ may also need to be updated for any
user-facing changes to note, like the state transitions of a server during
a cross-cell resize.

.. _resize guide: https://docs.openstack.org/nova/latest/admin/configuration/resize.html
.. _configuration guide: https://docs.openstack.org/nova/latest/configuration/
.. _server concepts guide: https://developer.openstack.org/api-guide/compute/server_concepts.html


References
==========

.. [1] Proof of concept: https://review.openstack.org/#/c/603930/
.. [2] Shelve-based approach spec: https://review.openstack.org/#/c/616037/1/
.. [3] API delete confirm resize: https://github.com/openstack/nova/blob/c295e395d/nova/compute/api.py#L2069
.. [4] Mirror BDMs on revert: https://review.openstack.org/#/c/603930/20/nova/conductor/tasks/cross_cell_migrate.py@637

Stein PTG discussions:

* https://etherpad.openstack.org/p/nova-ptg-stein-cells
* https://etherpad.openstack.org/p/nova-ptg-stein

Mailing list discussions:

* http://lists.openstack.org/pipermail/openstack-dev/2018-August/thread.html#133693
* http://lists.openstack.org/pipermail/openstack-operators/2018-August/thread.html#15729

Code:

https://review.openstack.org/#/q/topic:bp/cross-cell-resize+(status:open+OR+status:merged)


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
   * - Train
     - Re-proposed and added the known issue for
       :ref:`personality files <personality-files>` and details hard
       deleting the instance and its related records from a cell DB.
