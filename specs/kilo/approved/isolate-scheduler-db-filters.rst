..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Isolate Scheduler DB for Instances
==================================

https://blueprints.launchpad.net/nova/+spec/isolate-scheduler-db

As part of the above blueprint, several scheduler filters have been identified
as directly accessing the nova db, or calling the nova compute API. These need
to be changed in order to allow the eventual separation of the scheduler into
its own service (i.e., the Gantt effort).


Problem description
===================

There are three scheduler filters currently that need to access the nova
compute API or the nova DB in order to work:

  * TypeAffinityFilter
  * SameHostFilter
  * DifferentHostFilter

The first needs to know all the flavors on a host, and the others need to know
the UUIDs of all instances on the host. Their current method of api/db access
prevents the scheduler from being separated as an independent service. These
filters need to be updated to use host state objects in the scheduler instead
of accessing the db directly or calling the nova compute API.

Complicating this is the fact that it should be expected that as deployments
upgrade their scheduler to Kilo, there will still be many compute nodes that
will still be running older, pre-Kilo software, and will not be able to keep
the scheduler updated with their instance information. We will need a way to
distinguish these so that we know to run the existing DB/API calls for these
nodes, and to recognize when they've been upgraded.


Use Cases
----------

Nova contributors wish to extend the functionality of the scheduler and intend
to break the scheduler out into the Gantt project. In order to do this
effectively, the internal interfaces around the scheduler and its filters must
be modified to remove direct access to the nova DB and API.

Project Priority
-----------------

This blueprint is part of the 'scheduler' refactoring effort, defined as a
priority for the Kilo release.


Proposed change
===============

Rather than have the filters make DB or API calls, we will add the instance
information to the host_state objects that are already being passed to the
filters. This is not a trivial task, and will require several steps.

Overview
--------

The steps needed to accomplish this are:

  - Scheduler queries DB at startup to get current instance information.
  - Scheduler stores the host:instance information in the HostManager.
  - ComputeManager sends updated instance information to Scheduler over RPC API
    whenever significant changes occur.
  - Scheduler updates its HostManager with these updates as they are received.
  - ComputeManager periodically sends a list of its current instance UUIDs to
    Scheduler over RPC API.
  - Scheduler compares that to its view of instances. If there is a difference,
    Scheduler re-creates the InstanceList for that host and updates its
    HostManager.
  - The HostManager will add the instance information to the HostState objects
    created during a scheduling request
  - The filters that currently directly access instance info via direct calls
    to Nova will now base their filtering decisions on the information in the
    HostState objects instead.
  - Some deployments do not use filters that require instance information, and
    need to be able to turn off all of this behavior.
  - Allow for differing behaviors during rolling updates.

Changes to the Scheduler Startup
--------------------------------

The initial population of the instance information would be done when the
HostManager is initialized. It would first retrieve all instances, using a new
method ``InstanceList.get_all()``. It would then process these instances,
creating a dict with its keys being the host_name, and its values a 2-element
dict. This dict will have an 'instances' key, whose value will be the
InstanceList for that host, and an 'updated' key, whose value will default to
False, but which will be set to True when the Scheduler has received a sync or
update message from the compute node.  See the section below ``Handling Rolling
Updates to Compute Nodes`` for more details on why this is needed and how it
will be used.

This dict will be stored in the HostManager's ``_instance_info`` attribute that
represents the state of the instances on all compute nodes at scheduler
initialization time.  The 'updated' key will default to False, and get set to
True

While retrieving every instance at once can be a very heavyweight call, a
previous proposal to first get all hosts, and then run a query for all the
instances for each host was deemed to be a much slower approach, due to the
number of DB calls that would be required. Also keep in mind that this is only
done once on scheduler startup, so it would not come into play during normal
operation.

Changes to the ComputeManager's Operation
-----------------------------------------

Whenever a significant change happens to any of a compute node's instances
(create/ destroy/ resize), or when a new compute node comes online, the compute
node will notify the scheduler. For a new or resized instance, the current
Instance object will be sent. For a deleted instance, just the uuid of that
instance will be sent. This would be done via 2 new RPC API methods for the
scheduler. For create/update, the following method will be added:

  - update_instance_info(context, host_name, instance_or_list)

For terminated instances, the following method will be added:

  - delete_instance_info(context, host_name, instance_uuid)

The ComputeManager would have to have to make these calls in several places:

  * init_host()               - when a new host comes online (sends full
                                InstanceList)
  * _build_and_run_instance() - when a new instance is created
  * _complete_deletion()      - when an instance is destroyed
  * _finish_resize()          - when an instance is resized
  * shelve_offload_instance() - when a shelved instance is destroyed
  * _post_live_migration()    - when a migration has completed

All of the calls would come at the end of these methods, when we are sure that
the action has succeeded, and the Instance object has all of its attributes
populated, before making the call to update the scheduler.

The compute node would call the scheduler client, which would then send the
information for these calls to all running schedulers via an RPC fanout cast.
On the scheduler side of the call, this information would be used to update the
HostManager's '_instance_info' attribute. For updates, the HostManager will
locate the InstanceList for the specified host_name, and attempt to locate the
uuid of the received instance in the objects for that InstanceList, and if
found, it will remove the old object. The HostManager will then add the
received Instance to the InstanceList.objects list. For deletions, the
HostManager will locate the Instance object in the host's InstanceList, and
remove it.

In the case of the init_host() update, which will send a full InstanceList
object, the HostManager will replace the InstanceList for that host's entry in
its _instance_info attribute (if any) with the new InstanceList. If the host
key doesn't yet exist in the _instance_info dict, it will be added.

While passing entire Instance objects might be considered a 'heavy' approach,
it would be preferred over just passing the instance_type_id and uuid, for two
reasons:

  - Future filters that may be created which would rely on the instances on a
    particular host would be able to work with these objects, rather than
    having to modify the entire reporting system between the compute nodes and
    the scheduler to pass and store the new instance information.

  - The design for how this information is used will be much closer to what it
    will be when we separate the scheduler into its own service with its own
    database. Stripping this down to just the data that is needed now will mean
    more work later on.

Adding Periodic Sync Sanity Checks
----------------------------------

We must also take into account the fact that occasionally messages from a
compute node could get lost due to a failure in the messaging layer, or other
exceptional problem, and that this would result in the scheduler having a view
of the instances on the compute nodes that would not be accurate. To minimize
the difference between the actual state of instances on a compute node and the
view of that state that is held in the HostManager, the compute nodes will
periodically create a list of their instances' UUIDs, and pass that to the
scheduler client.  The following RPC API method will be added for this purpose:

  - sync_instance_info(context, host_name, instance_uuids)

This would be called as a periodic task, with a new CONF setting to handle the
frequency.

When the Scheduler receives this sync notification, it will construct the list
of uuids in the HostManager's _instance_info attribute for the specified
host_name, and compare it to the list it received. If they match, no further
action is needed. But if there is any discrepancy, it must be assumed that
there has been some unusual interruption of the normal update process, and that
the view of the instances for that host_name is not valid. It would be best to
simply have the Scheduler call InstanceList.get_by_host() and then replace the
InstanceList in the HostManager._instance_info for that host with the retrieved
values. It could also be possible to have the Scheduler retrieve individual
Instance objects for the uuids in the notification that are not in the
HostManager, and delete the instances that are in the HostManager but not in
the notification, but if we are in an obvious error state, it would be better
to start fresh and be sure that the two versions are in sync.

Since a host can continue to send updates while the HostManager is recreating
the InstanceList, all of the methods that can change the view of a host will be
decorated with a semaphore lock to avoid contentions.

Note that neither of these approaches will help the situation where an instance
has been resized and the message to the scheduler was lost. Since the UUIDs in
both the sync list and the HostManager list will match, no discrepancy will be
detected. It would be possible to change the sync to send tuples of
(instance_uuid, instance_type_id), but this option was discussed at the
midcycle meetup, and rejected as unnecessary. It is mentioned here just for
completeness.

Changes to the Scheduling Request Process
-----------------------------------------

The HostManager.get_all_host_states() method would be augmented to add the
InstanceList for each host to the host_state object. These host_state objects
are passed to the filters, and the filters would then access information about
instances directly from the host_state object instead of making DB/API calls.

Opting Out of Instance Notification
-----------------------------------

Many deployments do not use any of these filters, so they don't need the
scheduler to have current information about the instances. It would be wasteful
to have them constantly sending information that will never be used, so we will
add a new CONF setting that will default to True. If a deployer knows that
their setup doesn't use any of these filters, they can change that to False.
Compute nodes will read this setting at startup, and if it is False, they will
not update the scheduler when their instances change, nor send periodic sync
messages. Similarly, the HostManager would see this setting and know not to
bother to create the instance cache at startup, nor add instance information to
the HostState objects.

Handling Rolling Updates to Compute Nodes
-----------------------------------------

Since we cannot assume that all compute nodes will be updated to Kilo when the
scheduler is updated, we also need to handle the situation where we do not have
current information about the instances on a compute node, since pre-Kilo nodes
will not be doing the instance information updates described above. Without
those updates, we can't rely on the version of the InstanceList in the
HostManager, so we must query the DB each time there is a scheduling request.
To track this, the entry for each host in the _instance_info attribute will
have a value that is a two-element dict: one to hold the InstanceList, and the
other to hold a status indicator. This value will be set initially to False,
meaning that we don't yet know whether the compute node is running a version of
software that will properly update the scheduler with its instance changes.
Once we receive an update/delete/sync message from a host, we know that it is
running at least a minimal version to trust the Scheduler's view of the
instances, and we can use that for the filters.

This design will mean that some extra calls to the DB to get InstanceLists will
be needed when the Scheduler first starts up, as it will not yet be able to
trust the InstanceList information for any host until it has received at least
one update or sync message from that host. This is preferable, however, to the
Scheduler making improper decisions based on incorrect information.

Alternatives
------------

An alternative, and overall much cleaner, design would be to add the
InstanceList as a lazy-loaded attribute of the ComputeNode object. When the
scheduler starts up, instead of only storing a dict of (host_name:
InstanceList) values, a ComputeNodeList would be retrieved and stored in-memory
by the HostManager. There would be no more reason to call
``_get_all_host_states()`` with each scheduler request, but care would have to
be taken so that any changes to the hosts themselves are also propagated to the
scheduler.  But while this would be overall a cleaner approach and more in line
with where we want to take the scheduler, it was felt that this exceeded the
scope of the current blueprints.

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

There will be some improvement as a result of each of the three filters not
having to make a DB or API call for each host, but this will be minimal and is
not the driving force behind making these changes.

Other deployer impact
---------------------

Deployers will have to assess their use of these filters that require instance
information about a host, and update their config files to disable the tracking
of instances by the scheduler if it is not needed.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  edleafe

Other contributors:
  None.

Work Items
----------

  - Add a new CONF option to turn off instance updates from the compute
    manager, and to turn off the Scheduler gathering instance information and
    adding it to the HostState objects for filters.
  - Update the Scheduler to obtain the initial state of instances on compute
    nodes upon startup, unless the CONF flag for this behavior has been turned
    off.
  - Modify the methods of the ComputeManager listed in the 'Proposed change'
    section above, so that upon success, they call the appropriate method to
    pass the change to the scheduler, unless the CONF flag for this behavior
    has been turned off.
  - Add a new periodic task method to the ComputeManager to send
    a list of instance UUIDs to the _sync_scheduler_instance_info() method,
    unless the CONF flag for this behavior has been turned off.
  - Add a new CONF setting to control the interval for the above periodic task.
  - Create the methods in the ComputeManager class to take the parameters
    passed by the various methods and pass it to the scheduler client.
  - Add the RPC API calls to the SchedulerAPI class for the Scheduler client to
    call when receiving notifications from compute about instance changes.
  - Add methods to the Scheduler that will accept the information passed by the
    RPC API calls and properly update the HostManager's view of the
    InstanceList for the given host.
  - Add a reconciliation method to the HostManager to compare the uuid values
    for the host in its _instance_info attribute with the values passed by the
    host's sync call, and re-create the InstanceList if they don't match.
  - Update the HostManager's _get_all_host_states() to add the InstanceList
    information to each host that supports this version, unless the CONF flag
    for this behavior has been turned off. For hosts running older versions,
    make the InstanceList.get_by_host() call to get the information, and add
    that information to the HostState object.
  - Remove the current db/api calls in the filters, and modify the code to look
    for the InstanceList information in in the host_state object instead.
  - Add tests that verify that the CONF settings for turning the instance
    updates on/off are respected.
  - Add tests that verify that changing the version for a compute node changes
    how the HostManager handles adding instance information to the HostState
    objects.


Dependencies
============

None.


Testing
=======

The filters already have sufficient test coverage, but these tests currently
mock out the db/api calls. They will have to be updated to reflect the new
implementation.

The tests for the ComputeNode object will have to be updated to test that the
proper calls are being made in the required methods, and that the CONF flag is
properly respected.

The new behavior in the HostManager will also require that new tests be added
to cover these changes.


Documentation Impact
====================

There will need to be appropriate documentation for the new CONF settings that
will be added to turn off instance tracking by the scheduler, and to set the
sync period for compute nodes.


References
==========

This work is a subset of the effort outlined in this spec:

https://review.openstack.org/#/c/89893/
