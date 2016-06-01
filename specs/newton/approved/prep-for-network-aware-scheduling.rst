..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Prep work for Network aware scheduling
==========================================

https://blueprints.launchpad.net/nova/+spec/prep-for-network-aware-scheduling

Change how we talk to neutron to allow us in the future to implement
network aware scheduling.

Problem description
===================

Some IP subnets can be restricted to a subset of hosts, due to an operators
network configuration. In this environment, it means you could build somewhere
that has no public IPs available. This is being added into Neutron by the
Routed Networks feature.

To make this possible, we need to know the details of all the user's requested
ports, and what resources are required, before asking the scheduler for a
host. In addition, after picking a location, we should check that there is
an IP available before continuing with the rest of the build process.

As an aside, the allocate_for_instance call currently contains both
parts of that operation and has proved very difficult to maintain and evolve.
Splitting that code into a separate get/create ports and bind ports phase
should help make that code easier to navigate.

Use Cases
---------

This is largely a code refactor.

Proposed change
===============

The first step is to split the nova-compute manager's allocate_for_instance
into two distinct phases: get/create ports and bind ports. Currently we create
ports or update ports, depending on if they were passed in. This changes the
logic to optionally create a port, then later always update the port with the
binding details.

Second, we want to move the get/create ports before the scheduler is called.
In terms of upgrades, we need to ensure old compute nodes don't re-create
ports that the scheduler has already created. Similarly, when deleting an
instance, the old node should correctly know which ports were created by Nova
and can be deleted.
For nova-network users, the get/create ports can be a noop.

The third step is to move the port update into the conductor, right after
the scheduler has picked an appropriate host. We will not be able to run
this code until all compute nodes have been upgraded to the newest version.
Until all nodes have been upgraded, the new nodes will still have to run this
code on the Compute node. While annoying, this move is only to help with
faster retries, and as such, should not block any progress. Note this port
update step includes setting the host on the port, and in the future will
be the point an IP is assigned, if the port does not yet have an IP.

There are still some open questions around MAC address updates that occur
currently during the port creation. This process is only required for
ironic based VMs. The current state of this code is breaking our ability
to boot ironic instances with ports created outside of Nova. Resolving this
issue may delay this effort. DNS updates are not expected to change during
this transition, but as this work progresses I expect other issues similar
to the MAC address issue to come to light.

For nova-network, we can run the existing allocate-for-instance logic in the
conductor, after the scheduler is called. For cells v1 users, this should
correctly be in the child cell conductor. For cells v2 users, it doesn't
matter that this is in the api conductor.

Alternatives
------------

We could attempt to add more complexity into the existing
allocate_for_instance code. But history has shown that is likely to create
many regressions.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

Eventually it could mean we don't need any neutron related credentials on
any of the compute nodes. This work will not achieve that goal, but it is a
step in the right direction.

Notifications impact
--------------------

Notifications may now have a different host and service, but they should
be otherwise identical.

Other end user impact
---------------------

None

Performance Impact
------------------

Currently the neutron port binding is done in parallel with other long running
tasks that the compute node performs during the boot process. This moves the
port creation and binding into the critical path of the boot process.

When Nova is creating ports for users, instead of just calling port create
with all the parameters, will now first create the port and later update the
port. This will slightly increase the load on the Neutron API during the boot
process. However this should be minimal, as we are not duplicating any of
the expensive parts of the process, such as port binding and IP allocation.

This also generally moves more load into the nova-conductor nodes, but on the
upside this reduces the load on the nova-compute nodes.

Other deployer impact
---------------------

We will need the neutron credentials on nova-conductor, which may not
currently have been happening.

Developer impact
----------------

Improved ability to understand allocate_for_instance, and its replacements.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  John Garbutt (IRC: johnthetubaguy)

Work Items
----------

* Resolve how MAC address allocation will work in this new system
* Split allocate_for_instance into two functions
* Move create/get port call into the conductor, before calling the scheduler,
  such that allocate_for_instance no longer creates ports, no op for nova-net.
  This is likely to be achieved by adding a new method into the network API
  for both neutron and nova-net.
* Move the remainder of allocate_for_instance call into conductor, for both
  nova-net and neutron

Dependencies
============

None

Testing
=======

Grenade + neutron should cover this well.

Documentation Impact
====================

None

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced

