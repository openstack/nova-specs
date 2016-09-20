..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Ironic: Multiple compute host support
=====================================

https://blueprints.launchpad.net/nova/+spec/ironic-multiple-compute-hosts

Today, the Ironic virt driver only supports a single nova-compute service.
This is clearly not viable for an environment of any interesting scale;
there's no HA, everything fails if the compute service goes down. Let's fix
that.


Problem description
===================

Computers are horrible things. They die sometimes. They crash processes at
random. Solar flares can make bad things happen. And so on and so forth.

Running only one instance of nova-compute for an entire Ironic environment
is going to be a bad time. The Ironic virt driver currently assumes that only
one nova-compute process can run at once. It exposes all resources from an
Ironic installation to the resource tracker, without the ability to split
those resources out into many compute services.

Use Cases
----------

This allows operators to avoid having a single nova-compute service for an
Ironic deployment, so that the deployment may continue to function if a
compute service goes down. Note that this assumes a single Ironic cluster
per Nova deployment; this is not unreasonable in most cases, as Ironic should
be able to scale to 10^5 nodes.


Proposed change
===============

We'll lift some hash ring code from ironic (to be put into oslo
soon), to be used to do consistent hashing of ironic nodes among
multiple nova-compute services. The hash ring is used within the
driver itself, and is refreshed at each resource tracker run.

get_available_nodes() will now return a subset of nodes,
determined by the following rules:

* any node with an instance managed by the compute service
* any node that is mapped to the compute service on the hash ring
* no nodes with instances managed by another compute service

The virt driver finds all compute services that are running the
ironic driver by joining the services table and the compute_nodes
table. Since there won't be any records in the compute_nodes table
for a service that is starting for the first time, the virt driver
also adds its own compute service into this list. The list of all
hostnames in this list is what is used to instantiate the hash ring.

As nova-compute services are brought up or down, the ring will
re-balance. It's important to note that this re-balance does not
occur at the same time on all compute services, so for some amount
of time, an ironic node may be managed by more than one compute
service. In other words, there may be two compute_nodes records
for a single ironic node, with a different host value. For
scheduling purposes, this is okay, because either compute service
is capable of actually spawning an instance on the node (because the
ironic service doesn't know about this hashing). This will cause
capacity reporting (e.g. nova hypervisor-stats) to over-report
capacity for this time. Once all compute services in the cluster
have done a resource tracker run and re-balanced the hash ring,
this will be back to normal.

It's also important to note that, due to the way nodes with instances
are handled, if an instance is deleted while the compute service is
down, that node will be removed from the compute_nodes table when
the service comes back up (as each service will see an instance on
the node object, and assume another compute service manages that
instance). The ironic node will remain active and orphaned. Once
the periodic task to reap deleted instances runs, the ironic node
will be torn down and the node will again be reported in the
compute_nodes table.

It's all very eventually consistent, with a potentially long time
to eventual.

There's no configuration to enable this mode; it's always running. For
deployments that continue to use only one compute service, this has the
same behavior as today.

Alternatives
------------

Do what we do today, with active/passive failover. Doing active/passive
failover well is not an easy task, and doesn't account for all possible
failures. This also does not follow Nova's prescribed model for compute
failure. Furthermore, the resource tracker initialization is slow with many
Ironic nodes, and so a cold failover could take minutes.

Another alternative is to make nova's scheduler only choose a compute service
running the ironic driver (essentially at random) and let the scheduling to
a given node be determined between the virt driver and ironic. The downsides
here are that operators no longer have a pluggable scheduler (unless we build
one in ironic), and we'll have to do lots of work to ensure there aren't
scheduling races between the compute services.

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

This should improve performance a bit. Currently the resource tracker is
responsible for every node in an Ironic deployment. This will make that group
smaller and improve the performance of the resource tracker loop.

Other deployer impact
---------------------

None.

Developer impact
----------------

None, though Ironic driver developers should be aware of the situation.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jim-rollenhagen (jroll)

Other contributors:
  dansmith
  jaypipes

Work Items
----------

* Import the hash ring code into Nova.

* Use the hash ring in the virt driver to shard nodes among compute daemons.


Dependencies
============

None.


Testing
=======

This code will run in the default devstack configuration.

We also plan to add a CI job that runs the ironic driver with multiple
compute hosts, but this likely won't happen until Ocata.


Documentation Impact
====================

Maybe an ops guide update, however I'd like to leave that for next cycle until
we're pretty sure this is stable.


References
==========


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced but no changes merged.
   * - Newton
     - Re-proposed.
     - Completely re-written to use a hash ring.
