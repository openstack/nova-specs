..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================
Neutron Routed Networks
=======================

https://blueprints.launchpad.net/nova/+spec/neutron-routed-networks

In Neutron, there is a priority effort to support routed networks.  A routed
network, in this context, is a physical network infrastructure that implements
scaled networks by routing instead of large L2 broadcast domains.  For example,
deployers may have routers at each top-of-rack.  Instead of a single VLAN
covering the deployment, each rack would have its own VLAN and the routers will
provide reachability to the rest of the racks over L3.  `Operators want Neutron
to model this like a single network`__.  This has implications for Nova
scheduling and possibly migration.

__ operators-rfe_


Problem description
===================

`Neutron has a spec`__ for how this will be handled in there.  Each L2 network
is referred to as a segment.  Other terminology is in discussion in the spec.

__ neutron-spec_

For Nova, this has a couple of specific implications.  First, IP subnets will
have affinity to particular network segments.  Second, compute hosts will have
L2 reachability to (typically) only one segment within an network.  This means
that IP addresses assigned to ports are constrained to a potentially small
subset of compute hosts.

Currently, Nova requires an IP address on a port.  If that requirement were
kept, and that IP address is constrained to a small subset of compute hosts,
then the scheduler would have to constrain scheduling to that subset.  This is
a pretty severe artificial constraint on the scheduler.  To avoid it, Neutron
needs to be able to leave the IP address unassigned until after the port is
bound to a host.  After host binding, Nova can still fail the build for a
deferred IP port if an IP is still not allocated.

A related but much less severe constraint is that of IP availability across
segments.  Some segments might be exhausted and that should be considered by
the scheduler.  This is a resource that is under the control of Neutron and
hence will need `a resource provider created`__ to manage it for the Nova
scheduler.

__ resource-providers-spec_

For move operations involving the scheduler (e.g. live migrations), the VM
already has an IP address.  For that IP address to continue to work, the VM
must be migrated to another host with reachability to the same network segment.
Forced move operations that bypass the scheduler may cause a failure at binding
time if the segment is not available on the new host.

Use Cases
----------

In the following use cases, there is an assumption that all segments in Neutron
can be associated with one or more aggregates in Nova via the `proposed new`__
`openstack resource-pool create` and `openstack resource-pool add aggregate``
commands and associated REST API.

__ generic-resource-pools_

#. User has a port without a binding to a segment and provides it to nova boot.
   Such a port will not have an IP address until after the scheduler places the
   instance and the port gets bound to that host.  Then, Neutron can assign an
   IP address from a segment which that compute host can reach.

   In this use case, the scheduler must take into consideration the
   availability of IP addresses in each of the segments.  For example, there
   could be some segments in the network which are out of addresses completely.

   - A similar use case is to add an additional port to an existing instance.
     In this case, the segment and IP address of the new port will be set when
     the new port is bound to the compute host.  Since the port was unbound to
     begin with, there should be no restriction.

     Binding may fail in this case if all of the segments available to the host
     are out of IP addresses.

#. User has a port that has an IP address and thus is effectively attached to a
   segment (but not bound to a host).  He/She provides it to nova boot.  Nova
   will ask Neutron for the segment to which the port is bound by getting the
   details of the port.  Given that segment, the scheduler should place the
   instance on a compute host belonging to the corresponding aggregate.

   - A similar use case is to add an additional port to an existing instance.
     In this case, the segment of the new port must match a segment available
     to the instance's host.  If not, adding the port to the instance should
     fail.

#. User calls Nova boot and passes a network id.  The Nova scheduler will call
   Neutron to create a port, will place the instance, and then will call
   Neutron to update the port with binding details.  Neutron will use the host
   binding to set the segment and allocate the IP.

#. Any move operation calling out the scheduler.  In this case, the port
   already has an IP address.  That IP address is only viable in the same
   segment.  The scheduler must only consider target hosts that belong to the
   same segment (or aggregate).

Proposed change
===============

Neutron will be a resource provider as described in the `generic resource pools
specification`__ and its dependencies.   I imagine that Neutron will create and
maintain aggregates corresponding to its segments so that Nova has the same
mapping as Neutron does of hosts to segments.

__ generic-resource-pools_

Next, Neutron creates a resource_pool for each of the segments.  The pool has a
resource class (e.g. "IPV4_ADDRESS" or "IPV6_ADDRESS") in common with other
resource pools but each pool is specific to a segment id.  The linkage is set
by setting the UUID of the resource pool equal to the UUID of the segment in
Neutron.  Resource pools are linked to the host aggregates.

The resource pool has a record in an inventories table for IPs as a resource
class.  It effectively gives the capacity of the pool from Nova's perspective::

  capacity = (total - reserved) * allocation_ratio

Neutron will call Nova's REST API to set "total" to the size of the allocation
pool(s) on the subnets.  This will remain mostly static but could change if the
allocation pool is updated in a subnet-update call.  The allocation_ratio will
always be 1.0 in this use case.

Neutron sets reserved to the total number of addresses which are consumed
outside of Nova's purview.  This includes overhead stuff like dhcp and dns
consumed from the subnets' allocation pool which Neutron shares with Nova.
This is expected to remain mostly constant but might change a little more often
than the total if new overhead ports are allocated in Neutron.

The allocations table indicates how much of the capacity has been consumed by
Nova.

There can be a race to consume IP resources for any given segment.  In current
Nova, the claim is made on the compute node after scheduling is done.   This
can result in a race to consume IPs if the IP resource is getting low.  With
the claim being made by the compute node, a failure to collect the claim can be
very costly since the compute node has already started the process of claiming
and consuming other resources.

To reduce the cost of a failed claim this spec depends on `John G's spec`__ for
pre-allocating before scheduling and moving the port update to the conductor.

__ prep-for-network-aware-scheduling_

Regarding the use cases where the user has a port and brings that port to Nova
to create an instance (or to add it to an existing instance), they appear the
same at first::

  nova boot --nic port_id=$PORT_ID

Nova will make a call to Neutron to get or create a port and will receive the
details of the port in the response.  In those details, Neutron will include
the segment_id of the each fixed_ip on the port if it is bound to a segment.
This segment_id will be used to lookup the resource provider for IP addresses
on the segment.

For Nova to allow deferring IP allocation on a port, a new attribute will be
added to the Neutron port called ip_allocation.  It will have one of three
values:  "immediate," "deferred," or "none."  Ports with "immediate"
ip_allocation act like ports do today:  it is expected that an IP will be
allocated on port create.  Ports with "deferred" ip_allocation will have an IP
address allocated on port update when host binding information is provided.
Ports with "none" in ip_allocation are not intended to have an IP address
allocation at all.  It is beyond the scope of this patch to handle ports with
"none."

Alternatives
------------

One alternative was considered around trying to eliminate races for IP resource
between Nova and Neutron.  It involved significantly more active maintenance of
the reserved field on the resource provider and required that the the
allocation was conditionally recorded depending on the scenario.

This method was rejected in favor of the current proposal for its complexity.

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

#. Users who create a port with Neutron and bring it to Nova will notice that
   the port doesn't have an IP address when the network is routed.

#. Operators will notice the use of host aggregates which correspond to
   Neutron segments and their corresponding resource providers.

Performance Impact
------------------

The preceding spec to `prepare Nova for network aware`__ has some performance
effects that should be noted here although this spec does not add to those.  It
moves port get/create to before the scheduler which adds some overhead.  It
also moves the port update to the conductor which will significantly reduce the
overhead involved when port update fails due to exhausted IP address resources.

__ prep-for-network-aware-scheduling_

Other deployer impact
---------------------

Since this work is co-dependent on work in Neutron, there are some upgrade
considerations.  If routed networks are not used in Neutron then there is no
problem.  Existing networks and new non-routed networks will still work the way
they do today.  Since routed networks are an optional new feature, this will
only affect operators who wish to take advantage of it.

The best thing for operators to do will be to upgrade both services before
attempting to configure a routed provider network.  However, I'll discuss the
implications of rolling upgrades.

Consider if the Neutron API is upgraded and Nova is not.  Neutron will not have
the generic resource provider API endpoint available.  Neutron will need to
handle this gracefully taking advantage of microversioning in the Nova API.
Neutron will poll infrequently to discover when Nova has been upgraded and will
make use of the API when it becomes available.

In the meantime, it will be possible to create routed networks in Neutron but
scheduling will not be IP resource aware.  So, if segments run out of
addresses, boot failures will happen when a VM is scheduled to these segments
when Nova attempts to create a port and that fails.

Finally, the deferred IP allocation use case will not work because Nova will
refuse to use a port without an IP address until it has been upgraded.  The use
cases that don't involve deferred IP allocation will work until the above IP
exhaustion problem is encountered.

If Nova is upgrade and Neutron is not, then there is no problem because routed
provider networks and deferred IP address ports are not possible.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

* `Miguel Lavalle <https://launchpad.net/~minsel>`_
* `Carl Baldwin <https://launchpad.net/~carl-baldwin>`_

Work Items
----------

* Get segment_id, if available, from the port in the pre-schedule phase on the
  conductor.  Use that segment_id to look up the resource provider for IP
  address.

* Allow deferred or no IP addresses on ports by looking at the ip_allocation
  attribute on the port.

* Neutron to curate host aggregates and resource pools within Nova.  (This is
  Neutron acting as a client to the Nova API, isn't it?  So, it isn't really a
  Nova work item.)

Dependencies
============

This is co-dependent on the `Neutron spec`__ mentioned above.  Also depends on
the `resource providers`__ which has merged in Nova and the newly created `spec
to prepare for network aware scheduling`__.

__ neutron-spec_
__ resource-providers-spec_
__ prep-for-network-aware-scheduling_


Testing
=======

All new functionality will be covered with unit tests.  We'll be looking to
create a multi-node job to run on Neutron and Nova which tests out routed
networks.  It will include tests specifically for the use cases mentioned in
this spec.


Documentation Impact
====================

The OpenStack Administrator Guide will be updated.


References
==========

.. _operators-rfe: https://bugs.launchpad.net/neutron/+bug/1458890
.. _neutron-spec: https://review.openstack.org/#/c/225384/
.. _prep-for-network-aware-scheduling: https://review.openstack.org/#/c/313001/
.. _resource-providers-spec: https://review.openstack.org/#/c/225546/10/specs/mitaka/approved/resource-providers.rst
.. _generic-resource-pools: https://review.openstack.org/#/c/300176/16/specs/newton/approved/generic-resource-pools.rst


History
=======

None
