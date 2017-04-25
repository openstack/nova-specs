..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Scheduler claiming resources to the Placement API
=================================================

https://blueprints.launchpad.net/nova/+spec/placement-claims

Have the Nova scheduler create allocation records in the placement API after
selecting a compute host and conductor delete those allocations on a reschedule
or move operation.

Problem description
===================

The scheduler currently calls the Placement API in order to get a list of
ResourceProviders that match a specific request made of amounts of resource
classes. Currently, the ResourceTracker (RT) in the nova-compute service is
responsible for updating inventory and allocation values for resource
providers, e.g. compute nodes, in the Placement service. The process of
updating allocation values in the RT is called a 'claim'.

While this model fits very well for a cloud having lots of capacity left, but
in more resource-constrained environments can lead to contention and an
increase in retry operations.

In this spec, we propose to have the scheduler allocate resources instead of
the compute node.
Given the Placement API does not implement all the scheduler filters and
weighers, the proposal is that the scheduler would first get a list of
resource providers, iterate over those with the help of filters and weighters,
and once it decrements the resource usage in the consume_from_request()
synchronous operation, it would post the allocations against the found target.
In this way, we both reduce the occurrence of retry operations as well as the
time period that race conditions can occur.

Use Cases
---------

As an operator, I'd like to minimize the amount of time between requesting a
resource and actually consuming that resource in order to avoid cascading
scheduling failures.

Proposed change
===============

The spec targets to modify when/where allocations are created and instead of
letting the ResourceTracker (RT) post the allocations, we propose the scheduler
preemptively write those allocations. We will use a service version check in
the scheduler to ensure all compute hosts in the system can handle a request
that has had allocations already written by the scheduler service.

Then, the compute service would query the Placement API for allocations related
to that specific consumer (the instance) and if existing, then the RT would not
call the Placement API to add allocations during the claim operation. That
claim contextmanager will itself become lightweight because it will only verify
PCI and NUMA resources that aren't yet handled by the Placement API.
Given virt drivers can return the overhead of a specific instance that is then
taken into account for claiming the resource in the RT, and given overheads
are very specific per hypervisor type, version and instance flavors, a proposed
trade-off for having placement be able to correctly verify those overheads is
to ask operators to update the current 'reserved' configuration options that
relate to the hypervisor offset amount needed for running by capping it to the
maximum amount per resource class they think it would require to run on the
compute node.

Move operations and reschedules (if unexpected failures happen when spawning
the instance) will delete original allocations by having the conductor call
DELETE /allocations/{instance_id} and be done with it.

When terminating an instance, the associated allocations are already deleted
from the Placement API when the instance is physically removed on the compute
host. That said, there is an existing bug report [1] for local deletes (if the
RPC compute service is not up when deleting the instance) that don't delete the
allocations, so the bugfix will be a work item for that spec.

That all said, there is a current problem with reschedules for Cells V2 where
the compute calls back conductor. Unfortunately, given it would call a cell
conductor, the conductor wouldn't be able to call again the scheduler given the
latter is not in the same message queue. While it's a problem for cells v2, we
agree it's a problem not related to this spec.


Alternatives
------------

We could pass the allocations thru RPC when calling the compute service by
adding them as a method argument, but given the Allocation objects are a
Placement specific model, we prefer not use them directly in Nova.

One last argument could be about where to call Placement API for both creating
allocations and deleting them, whether in the conductor or in the scheduler
services, but we leave that for a review discussion during the implementation.
We possibly reserve ourselves to verify the performance between those two
alternatives using some benchmark tooling.

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

Placement HTTP calls would be made within the scheduler service instead of
compute services for allocating instances.

Other deployer impact
---------------------

Rolling upgrades would keep the legacy behaviour until all compute nodes are
fully upgraded and the transition would be automatic.

Operators would need to amend ``reserved_host_disk_mb``,
``reserved_host_memory_mb`` and a newly-created ``reserved_host_cpus``
configuration options in order to accept instance overheads provided by each
hypervisor type. The values of those config options should be equal to the
amount they want to leave for each hypervisor plus the maximum number of
instances by the least-sized flavor times the overhead for that flavor.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sylvain-bauza

Other contributors:
  None

Work Items
----------

* Fix the bug [1] about not deleting allocations for local instance deletions.
* Add a new ``reserved_host_cpus`` config option and use it by the RT.
* Amend RT to filter out allocations for instances that don't have a host set
  yet when it does self-heal check.
* Make compute nodes GET /allocations/<instance_id> for verifying if already
  created, and if so, don't POST allocations to Placement service.
* Modify conductor to DELETE /allocations/<instance_id> if this is a reschedule
  or a move operation.
* Modify scheduler to POST allocations to Placement if all computes are new.

Dependencies
============

None.


Testing
=======

Nothing really fancy new, classic coverage of unit and functional tests.

Documentation Impact
====================

None.

References
==========

[1] https://bugs.launchpad.net/nova/+bug/1679750
[2] https://etherpad.openstack.org/p/nova-pike-claims-in-scheduler
