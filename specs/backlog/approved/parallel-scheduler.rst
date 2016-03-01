..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Parallel Filter Scheduler
==========================

This backlog spec discusses the issues around parallelism and the current
Filter Scheduler in Nova. This is particularly interesting for when
migrating existing cells v1 users to cells v2.

Problem description
===================

We need the nova filter scheduler to work well in typical public cloud
even after they have migrated from cells v1 to cells v2.

Some key observations about the current nova-scheduler:

* If you running two nova-scheduler processes they race each other, they
  don't find out about each others choices until the DB gets updated
  by the nova-compute resource tracker.
  This has lead to many deployments opting for an Active/Passive HA setup
  for the nova-scheduler process.

* The resource tracker has the final say on if an instance can fit.
  If the request ends up on a full compute node, the build errors out,
  and lets the retry system find an different compute node to try.
  However, we stop retrying after three attempts, and this extends build
  times for users, so its best to avoid these retries.

* Deployers often chose to fill first, to ensure they keep room for
  larger flavors they offer. They then use the IO-ops filter to ensure you
  don't have too many builds happening on the same node at any time.
  Adding these together, this makes the above races much worse.

* Randomization of decisions has been added to reduce the impact of the
  races, but this means its making 'worse' decisions.

* Querying the DB is the most expensive part of the scheduling process.

* The C based DB driver and eventlet means the scheduler performs best
  when the eventlet thread pool is very small, ideally less than 5.
  Without that, you find it makes several DB calls before processing
  the (now stale) information it has fetched from the DB.

* The Caching Scheduler was added to periodically update the host state
  in a periodic task, so no user request has to wait for the DB query.
  It uses consume_from_instance to update the cached state for future
  requests. Note its not until the next poll period that the data will
  be refreshed to include information about any delete requests.
  The state is also local to each scheduler process.

* Until the end of kilo, many filters and weights also made DB queries to
  fetch information such as host aggregates. The work help isolate the
  scheduler from the rest of nova has removed all those extra DB calls,
  so it is now only periodically fetching the state from the DB.

Cells v1 shards the system so there is a single nova-scheduler per cell.
Each cell typically has several hundred hosts.
When a build request comes in, cells v1 first picks a cell, then inside
that cell, the regular nova-scheduler picks one of the compute nodes in
that cell. The API cell is given a list of slots from the nova-cells process
in each of the child cells. The child cell's nova-cells process periodically
looks at the state of all the hosts, alongside the current set of flavors,
and reports the number of slots each cell has available.
The slots are based on memory and disk, and not actually per flavor.
This system has several limitations, but the key ones for this discussion are:

* Once in a cell, the build retry attempts only happen between compute nodes
  within that cell.
  If you fail to build in a cell, there is no way to try another cell.
  If a cell gets full, there is no way to move a VM to another cell if it
  needs to be resized up.

* The reported slots have hidden dependencies.
  If you have space for a 2 GB VM, the system also reports two slots for a
  1 GB VM. There is no way to express that those three slots are related.
  If the scheduler chooses to use the 2GB slots, when the next request
  uses one of the 1GB slots, when it reaches that cell it will discover
  the capacity was already used the by previous request.

* The current cells scheduler doesn't update its in memory state between
  scheduling decisions, and has no randomization.
  Consider two cells, one with 12x1GB slots another with 10x1GB slots.
  If you get 15 requests for a 1GB slot, they all get sent to the cell
  reporting 12 slots. 2 of those build request will fail because that cell
  has no room.
  There are plans to randomly distribute builds between those slots, but
  that just limits the impact of this problem, rather than eliminating it.

* This is a described in the Google omega paper as "two level scheduling"

So in summary, the current nova-scheduler works best when:

* there is a single nova-scheduler process running

* it periodically refreshes its state from the DB

* it updates its in memory state with any previous decisions it has made

* it makes one decision at once, zero parallelism

This is the backdrop in which we need to look at new ways to scale out the
nova-scheduler, so we are able to scale to a level where existing cells v1
user are able to move to cells v2 where a single nova-scheduler deployment
has to deal with the current load 15-20 nova-schedulers are dealing with
today.

Use Cases
----------

Consider a deployment where you have more than 10k hypervisors,
with build request bursts of at least 1k within a 15 min period.

This is particularly relevant to cells v1 users that are going to be
migrate to cells v2.

Proposed change
===============

None

This spec is to agree the problem, and list some possible solutions.

Alternatives
------------

Multiple Scheduler Future
++++++++++++++++++++++++++

Nova has two schedulers, the random scheduler and the filter scheduler.
In the future, its increasingly likely there will be multiple schedulers
that work well for particular use cases and usage patterns.

With that in mind, I am going to focus on replacing the typical
public cloud use cases as described above.

Moving away from filters and weights
+++++++++++++++++++++++++++++++++++++

An alternative to the existing scheduler is to have nova-compute nodes pull
build requests from a shared queue, rather than being pushed work from a
central scheduler.

This works well for spread first, but requires some careful co-ordination
to make a fill first scheduler work. You probably need a central system to
give a new compute node permission to pull from the queue, or something like
that.

If you pull a message from the queue, and discover you are unable to service
that request you could put that message back on the queue. Ideally you would
shard the number of queues to limit the cases where such retries are needed.
Although, its hard to do that with per tenant affinity and anit-affinity
rules.

While I really want someone to explore building a driver like this,
this spec is not considering this approach. It will instead focus on a more
direct replacement for the current filter scheduler.

Partitioning the Filter Scheduler
++++++++++++++++++++++++++++++++++

A great way to reduce the size of a problem, is to split the larger
problem into smaller pieces. Lets look at this in more detail.

One major issue is interference between different schedulers. Ideally
we don't want multiple schedulers assigning work to the same nova-compute
nodes, as they will be competing with each other for the same resources.
Ideally each scheduler would be looking a different subset of hosts.

Fighting this requirement are cluster wide behaviors, such as affinity and
anti-affinity rules, where ideally we need to know the full state of the
system, rather than just looking at a subset of the system.

Its possible to have a dynamic partitioning, but for simplicity, I am going
to focus on static partitions of the system.
The problem with a static partition is that they tend to have capacity
planning implications. If a subset of all requests get routed to a particular
set of hosts, then you need to ensure you increase the number of hosts to
match the demand for that subset of hosts.

In cells v1, the top level scheduling was used to try and spread the load
between lots of groups that get added as you expand, but this two level
scheduling caused lots of other races of its own.

With these ideas at the back of my mind there is an interesting use case
we can consider:

* Certain groups of hosts can have specific hardware mapped to
  specific flavors.
  i.e. SSD vs non-SSD local storage vs all storage form cinder (no local disk)

* Keeping Windows and Linux VMs on different sets of hypervisors is common
  place, to allow for the best utilization of bulk license savings.
  This is a very similar distinct split between hosts based on the users
  build request.

Lets consider having a separate nova-scheduler cluster for each of these
groups of hosts. We can route requests to each scheduler cluster based on
the request spec. The flavor is required in all build requests, and can route
you to one of each subset. Requests for global concepts such as affinity don't
really make sense across these groups of hosts, and its possible that the
request router could check these kinds of constraints.

In a cells v2 world, you would have multiple cells in each group. For
simplicity we can assume each complete cell would be registered to one
(and only one) of the scheduler clusters. In practice, we probably want each
host to know what scheduler it should report things two.

The nice property of this partition is that you need to do capacity planning
for each of these groups of hosts independently, regardless of how the
scheduling is implemented.

There are many other possible partitions, but this seems one of the simplest
and well help many of the large cloud users moving from cells v1 to cells v2.
Lets consider another partition, such as using hash of a tenant to
choose between some distinct subset of hosts. Here you need to have a very
large number of tenants and/or even usage across your tenants, otherwise
you end up having to expand capacity differently across each of the groups
as the demand from those different tenants goes up and down.
When each of those schedulers look at overlapping subsets of the nodes, you
improve the spread of resources, but you tent to end up with some interference
between the different scheduler clusters.

While some of these alternative partitioning schemes may well be useful once
we have some of the other enhancements discussed here, I am limiting the scope
of this spec to the simplest partitioning scheme, a distinct partitioning of
hosts based on the requested flavor, for the initial version.
The major downside of this approach is it limits the impact of partitioning to
the very largest cloud deployments, those where there are several distinct
groups of hosts that have their capacity managed separately.

Using the Resource Tracker to implement "distributed" locking
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

There have been various discussions about having the resource tracker persist
the resource claims it hands out, so those claims persist across a
nova-compute service restart. On top of that, we can add some RPC calls so the
nova-conductor, or any other node, would be able to acquire one of these
claims during VM move operations, such as resize and live-migrate, where you
don't want new VM builds taking up space you are about to use once you have
move the VM.
It was also discussed that these claims should expire after an amount of time
if the claim is not used. This should protect against failure modes where you
get a leak of capacity due to un-used resource tracker claims.
This moves what could be a distributed locking mechanism to a per nova-compute
locking system, that should mean there is much less lock contention, and
generally its a much easier problem to solve.

When the resource tracker reports its current available resources up to the
scheduler it would reduce the amount of free resources to take account of the
current claims on its resources.

Now consider if the scheduler was able to acquire one of these claims before
returning the chosen host to the nova-conductor. This would be moving the
claim request from the very start of the build process in nova-compute into
the scheduler.
This would allow the scheduler to build up a collection of claims for the
requested resources before returning the choice to the caller what resources
the scheduler has chosen. Should there be a problem detected, the scheduler
can perform retries until it gets all the claims required for the given
resource request made to the scheduler.

Putting this all together, you now see that the schedulers will start to see
each others decisions because the claims acquired by another scheduler show up
more quickly in the shared state.

Taking this a step further we could ensure that a scheduler waits for the
claim it just took to show up in the shared state before returning the
compute node choice to the scheduler's caller.

Another possible twist is to consider a claim system very similar to the
"compare and swap" DB call system. When the scheduler makes a claim, it could
tell the compute node only to give out that claim if the compute node still
has the same free resources and the scheduler currently things it has. If the
scheduler has a different view of the resources, it is should update its
internal state to see if this is still the best node to send the request.
It could be done by having a hash of the currently reported node state,
and comparing that. Its assumed such a hash would not change when an instance
goes from the claimed state to a state where it is using that claim.

It seems likely that a combination of these strategies should help ensure the
scheduler is able to deal with most races between other parallel schedulers
before returning the chosen compute node to the scheduler caller. This should
reduce the cost of any scheduler races that may still occur.

Moving from querying the DB state to consuming a stream of updates
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

As mentioned above, the most expensive part of the scheduling process is not
running through the list of filters and weights, it is getting updating the
current host state from the database.

We currently use the Caching Scheduler to reduce the cost of these DB calls,
but using stale data that gets updated in memory to reduce the impact of it
being stale.
And interesting alternative is to just consume the updates to the current
state, rather than having to fetch the full copy of the host state every time:
https://blueprints.launchpad.net/nova/+spec/no-db-scheduler

This is very similar to a shared state scheduler discussed in the omega paper.
In this case the shared state is implemented using an in memory structure in
each of the schedulers, with a stream of updates that are required being fed
to all of the consumers.

Should you need to re-start a nova-scheduler process, or start an additional
nova-scheduler process, they would need to go back to the "start" and consume
all the updates, so its state is in-sync with all the other schedulers, before
starting to service any requests.
Making sure all computes report their full state occasionally means there is a
point where you can trim the old updates and still get a full view of the
the full system.

The pain point of friction with the no-db-scheduler was the complexity of
maintaining the code that look a lot like the implementation of a DB log.
Being able to efficiently trim old updates, so any new schedulers have only
have a small amount of data to catch up.
It turns our Kafka has already implemented at lot of these semantics and is
has already been proven to work at an extremely large scale:
http://kafka.apache.org/documentation.html#introduction

It seems we should be able to create a kafka based system to get efficient
incremental updates to the current state of the system, rather than having to
make the expensive DB call to get the state for all the hosts we are
interested in.

Memory concerns
++++++++++++++++

There have been worries about the assumption we can store in memory a list
of all the hosts in the system, and their current state.

It seems that, in practice, this will be the least of our worries when it
comes to finding what limits the level of scale this solution can reach.

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

None

Other deployer impact
---------------------

Any solution will need a way to live upgrade from the existing scheduler.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee: None

Other contributors: None

Work Items
----------

None

Dependencies
============

None

Testing
=======

The existing tempest tests will be able to ensure the scheduler works as a
drop in replacement for the old scheduler.

The grenade tests (or a similar test) should be enhanced to test the migration
between the existing scheduler and this new scheduler.

It would be good to investigate some functional tests to stress test the
scheduler system, so we can simulate the race conditions that are being seen
in certain production scenarios, and prove is the new system improves things.

Documentation Impact
====================

None

References
==========

Google omega paper: http://research.google.com/pubs/pub41684.html

History
=======

None

