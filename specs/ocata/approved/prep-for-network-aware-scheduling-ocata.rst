..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
Prep work for Network aware scheduling (Ocata)
==============================================

https://blueprints.launchpad.net/nova/+spec/prep-for-network-aware-scheduling-ocata

Change how we talk to neutron to allow us in the future to implement
network aware scheduling.

This continues on from the work started in Newton:
http://specs.openstack.org/openstack/nova-specs/specs/newton/implemented/prep-for-network-aware-scheduling.html

Problem description
===================

Some IP subnets can be restricted to a subset of hosts, due to an operators
network configuration. In this environment, it means you could build somewhere
that has no public IPs available. The ability to manage IP addresses in this
way is being added into Neutron by the Routed Networks feature:

* http://specs.openstack.org/openstack/neutron-specs/specs/newton/routed-networks.html
* https://specs.openstack.org/openstack/nova-specs/specs/newton/implemented/neutron-routed-networks.html

To make this possible, we need to know the details of all the user's requested
ports, and what resources are required, before asking the scheduler for a
host. In addition, after picking a location, we should check that there is
an IP available before continuing with the rest of the build process.

As an aside, the allocate_for_instance call currently contains both
parts of that operation and has proved very difficult to maintain and evolve.
In newton, we changed the code to separate the update and create operations,
so we are now able to look at moving where those operations happen.

Use Cases
---------

This is largely a code refactor.

Proposed change
===============

In newton we have changed the code inside allocate_for_instance into clear
get/create and update phase. We need to complete the split, by ensuring the
network info cache contains all the info required to be shared between the
two phases of the operation (get/create ports and update ports).
Should a build request fail, and the build is retried on a different host,
the ports that Nova creates should be re-used for the new build attempt,
just like the ports that are passed into Nova. This bug fix requires the data
to be correctly passed in a very similar way, so will be the initial focus of
this effort.

Second, we want to move the get/create ports before the scheduler is called.
In terms of upgrades, we need to ensure old compute nodes don't re-create
ports that the conductor has already created. Similarly, when deleting an
instance, the old node should still correctly know which ports were created
by Nova and can be deleted when the instance is deleted, in the usual way.
For nova-network users, the get/create ports can be a noop.

To avoid problems across upgrades, the early creating of ports is not allowed
until all nova-compute nodes are upgraded to the version that understands if
a port has been created or not. Once all are upgraded, and credentials are
available on the nova-conductor node, ports will be created before calling the
scheduler.

The third step is to move the port update into the conductor, right after
the scheduler has picked an appropriate host. We will not be able to run
this code until all compute nodes have been upgraded to the newest version.
Until all nodes have been upgraded, the new nodes will still have to run this
code on the Compute node. While annoying, this move is only to help with
faster retries, and as such, should not block any progress. Note this port
update step includes setting the host on the port, and in the future will
be the point an IP is assigned, if the port does not yet have an IP.

It is useful to update the port bindings in the conductor, so any failure in
the port binding for a specific host can quickly trigger a retry. This is
particularly a problem when you have routed networks, and segments can run out
of IP addresses independently.

For nova-network, we can run the existing allocate-for-instance logic in the
conductor, after the scheduler is called. For cells v1 users, this should
correctly be in the child cell conductor, because each cells v1 cell has its
own separate nova-network instance with a different set of IP addresses.
(For cells v2 users, the networking is global to the nova deployment, so its
doesn't matter where that happens.)

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

To maintain our upgrade promise, we will fall back to the old behaviour for
one cycle to give deployers a warning about the missing credentials. The
following cycle will require the credentials to be present on nova-conductor.

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

* Split allocate_for_instance into two functions
* Move create/get port call into the conductor, before calling the scheduler,
  such that allocate_for_instance no longer creates ports, no op for nova-net.
  This is likely to be achieved by adding a new method into the network API
  for both neutron and nova-net.
* Move the remainder of allocate_for_instance call into conductor, for both
  nova-net and neutron

Dependencies
============

None (however, several things depend on this work)

Testing
=======

Grenade + neutron should ensure the pre-upgrade flow is covered, the regular
gate tests should ensure the post-upgrade flow is covered.

We should add functional tests to test the re-schedule flow. We might also
need functional tests to check the transition between the pre and post upgrade
flows.

Documentation Impact
====================

Need to describe the transition in the release notes, and release specific
upgrade documentation, at a minimum.

References
==========

* Previous work: http://specs.openstack.org/openstack/nova-specs/specs/newton/implemented/prep-for-network-aware-scheduling.html
* Neutron Routed network spec: http://specs.openstack.org/openstack/neutron-specs/specs/newton/routed-networks.html
* Nova Routed network spec: https://specs.openstack.org/openstack/nova-specs/specs/newton/implemented/neutron-routed-networks.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
   * - Ocata
     - Continued

