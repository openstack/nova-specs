..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Scheduler: Introduce HostState level locking
============================================

https://blueprints.launchpad.net/nova/+spec/host-state-level-locking

Nova FilterScheduler implementation even though inherently multi-threaded, uses
no locking for access to the shared in-memory HostState data structures, that
are shared between all active threads. Even though this means that most of
decisions that scheduler makes under load are not internally consistent, this
is not necessarily a huge issue for the basic use case, as Nova makes sure that
the set resource usage policy is maintained even due to races using the retry
mechanism [1]_. This can however cause issues in several more complex use
cases. A non exhaustive list of some examples would be: high resource
utilization, high load, specific types of host and resources (e.g. Ironic nodes
[2]_ and  complex resources such as NUMA topology or PCI devices).

We propose to change the scheduler code to use a lightweight transactional
approach to avoid full blown locking while still mitigating some of the race
conditions.


Problem description
===================

Our scheduler service is inherently multi-threaded as it currently runs an
oslo-messaging RpcServer using an EventletExecutor. This means that every
incoming RPC message for select_destinations will be dispatched in it's own
green thread.

Upon receiving the message, every green thread will read all ComputeNode states
from the database, and potentially [3]_ populate the internal global data
structure that holds the host states which will be used for filtering.

Further along, after choosing a host, each thread will call the
HostState.consume_from_instance() method on the chosen object, which will
"consume" the resources for the instance being scheduled from the chosen
HostState object. This is the equivalent of what Claims code does once the
request makes it to a nova-compute service, except instead of updating the
ComputeNode table, it updates the scheduler service's in memory HostState
object.

However since there is no mutual exclusion of threads between
the time a filter function ran and decide that the host passes, until a single
host state was chosen. A number of other concurrent threads could have already
updated the same host state. A classic race condition. Once we consider this,
some obvious avenues for improvement arise.

1. When calling consume_from_instance() we are basically doing a claim of
   resources on the host state, that may have changed since the filter function
   that decided to pass the host ran. At that point we have all the information
   to know early if a claim is going to fail and try to choose a different
   host. This is roughly equivalent to retrying a transaction.

   It is worth noting here that even though we may find that host seems like
   it will be failing, we may still want to choose it, as we don't ever drop
   the resources consumed on the HostState even after we register a retry from
   a already chosen compute host in this refresh cycle, so it may in fact be
   a false negative.

2. There needs to be some kind of locking that is granular enough so as not to
   cause too much unnecessary overhead, but also to allow for more consistent
   handling of HostState.


Use Cases
----------

There is no specific use case that this is aimed at. It is an internal
refactoring aimed at improving data consistency in the scheduler, and thus
overall effectiveness of placement decisions.

Project Priority
-----------------

Yes - This is work related to the scheduler, one of the priority topics for
Liberty.

Proposed change
===============

Firstly, it would be very useful to use the Claim logic instead (or inside) of
HostState.consume_from_instance() as there is almost complete duplication
there.

Next change that would be in the scope for this blueprint would be adding
synchronisation primitives around accessing and updating HostState fields.
A lightweight approach would be to not use any synchronisation primitives in
the filters, as access to the host state is a) read-only b) usually per
resource. consume_from_instance is the place where we want to make sure access
is synchronized, as once the host is chosen, it will need to have resources
consumed (remember - many concurrent threads could be trying to consume
resources from the same HostState) and if it fails any of the "claims", no
resources should be consumed. Updating the host state with fresh values after
a DB read should also be synchronized.

Final piece of the puzzle is modifying the FilterScheduler._schedule() method
to take into account the failure to claim in consume_from_instance() and try
the next host that passed the filters, or choose to ignore the local in memory
failure and risk a retry from the compute host.

It is worth noting that this proposal only looks at fixing data consistency
among threads of a single nova-scheduler process. Running several workers still
means that their internal state is going to be inconsistent between updates
from the database. Fixing this is outside of the scope of this proposal.

Alternatives
------------

There are a number of ways we could re-design the scheduler so that the issues
discussed in this spec become irrelevant. This blueprint aims to improve some
obvious issues with the current implementation of the scheduler without
changing the basic design.

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

Even though there will be overhead of synchronisation in every request after
this change which may decrease the average response time for basic workloads,
I fully expect this to massively improve the performance in conditions of a
large number of requests, or low overall cloud capacity (or specific resources
such as Ironic hosts), as it will significantly cut down on issued retries.

Other deployer impact
---------------------

There may be several config options deployers would need to consider. Defaults
may be chosen in such a way as to not change previous behaviour.

Developer impact
----------------

Developers would need to understand that there is now locking going on in the
scheduler, and consider this when making changes to the code, especially in
case of adding additional resources.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <ndipanov>

Work Items
----------

* Refactor Claim classes to not be directly dependent on the resource_tracker,
  so that they can be used in the scheduler code and possibly move out of the
  compute/ subtree

* Modify HostState.consume_from_instance() to use the Claim logic and acquire
  a HostState instance-wide lock for doing so.

* Modify HostState.update_from_compute_node() to acquire a HostState
  instance-wide lock for updating the host state.

* Modify FilterSchedule._schedule() method to expect a claim transaction
  failure and take appropriate action.

Dependencies
============

None

Testing
=======

As is usually the case with race problems, it is notoriously difficult
to come up with deterministic tests. Testing will be limited to unit tests
making sure that proper synchronisation primitives are called as expected.

Documentation Impact
====================

There may be an additional config option to turn on the transactional nature
of consume_from_instance() and possibly another one to tell the scheduler to
go ahead and attempt to land an instance even though a local claim failed.

References
==========

 .. [1] The Retry mechanism works kind of like a 2PC where the instance
    resource usage is consumed on the in memory view the scheduler has, but is
    only committed to the DB when the request makes it to the chosen compute
    host, and under a global resource lock.
 .. [2] This `bug <https://bugs.launchpad.net/nova/+bug/1341420>` shows that
    this is pretty bad in case of Ironic.
 .. [3] I say potentially because there is a check of a timestamp to see if the
    HostState has actually been updated more recently than the ComputeNode
    record (with in flight requests not yet claimed on their compute hosts).


History
=======

Optional section for liberty intended to be used each time the spec
is updated to describe new design, API or any database schema
updated. Useful to let reader understand what's happened along the
time.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced

