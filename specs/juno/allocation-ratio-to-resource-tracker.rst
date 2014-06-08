..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Move allocation ratios to resource tracker
==========================================

https://blueprints.launchpad.net/nova/+spec/allocation-ratio-to-resource-tracker

Move the definition and calculation of allocation ratios out of the scheduler
and into the resource tracker.

Problem description
===================

Allocation ratios are currently improperly defined in the scheduler. This leads
to efficiency problems due to the scheduler interfacing with the database
when it does not need to as well as recalculating adjusted resource usage
numbers when it does not need to.

The memory and CPU allocation ratios are currently controlled on a global or
per-aggregate basis, with the global configuration settings determined in the
core_filter and ram_filter filter modules in the scheduler, and the
per-aggregate allocation ratio overrides are stored in the aggregates table in
the database, with the core_filter scheduler filter performing repeated lookups
to the aggregates table to determine the allocation ratio to use when host
aggregates are in use in the deployment.

Allocation ratios are NOT scheduler policy, and should neither be defined
nor queried in the scheduler at all. Allocation ratios are simply a way for a
compute node to advertise that it has the ability to service more resources
than it physically has available: an overcommit ratio. Therefore, not only does
the total advertised amount of resources on a compute node NOT need to be
recalculated on each run of the scheduler to find a compute node for an
instance, but the resource tracker is the most appropriate place to set the
available resource amounts.

Proposed change
===============

We propose to move the definition of CPU and memory allocation ratios out of
the scheduler filters where they are currently defined (core_filter and
ram_filter) and into the resource tracker (nova.compute.resource_tracker).

Further, we propose to remove all calculation of the compute node's overcommit
ratio for both CPU and RAM out of core_filter.py and ram_filter.py.

This calculation will initially be moved into the host_manager.HostManager
class, which will store the real and adjusted available resource amounts for
each compute node in its collection of HostState structs. Because the current
resource tracker in Nova only accounts for a single compute node, we must,
for now, use the scheduler's internal resource tracker (HostManager) to track
all compute nodes' allocation ratios.

When constructing and refreshing its collection of these HostState structs, the
HostManager calls nova.objects.compute_node.ComputeNodeList.get_all(). We will
amend this particular call to include the host aggregate information for each
compute node. If the compute node belongs to any host aggregates, then the
overcommit ratio for CPU and memory shall be either the lowest ratio set for
any of the host aggregates OR the default global configuration ratio value.

The long-term goal is to enable each compute node in the system to have its
own settable allocation ratios and remove the need for this particular check
or calculation in the resource tracker or the scheduler itself. My personal
end goal is to align the scheduler's internal resource tracker with the code
in nova.compute.resource_tracker, but this particular blueprint is scoped
only to the relatively minor changes described above.

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

Even with the relatively minor changes introduced here, there should be a
performance increase for a single scheduler request due to fewer
calculations being made in each scheduler request. For deployments that
use host aggregates, performance improvements will be much greater, as
the number of DB queries per scheduler request will be reduced.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Implementation
==============

Work Items
----------

 * Modify nova.objects.compute_node.ComputeNode and ComputeNodeList() to be
   able to include host aggregate information for the compute node
 * Move the definition of the allocation ratios out of the filters and into
   nova.compute.resource_tracker, and then import_opt() in
   nova.scheduler.host_manager to bring in those allocation ratio definitions
 * Change the behavior in HostManager.get_all_host_states() to calculate
   resources available from either the host aggregate's min ratio or the
   global conf definition ratio

Assignee(s)
-----------

Primary assignee:
  jaypipes


Dependencies
============

None

Testing
=======

Some minor adjustments to the existing unit tests would need to be performed.

Documentation Impact
====================

None

References
==========

Mailing list discussion:

http://lists.openstack.org/pipermail/openstack-dev/2014-June/036602.html
