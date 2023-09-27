..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Ironic Shards
==========================================

https://blueprints.launchpad.net/nova/+spec/ironic-shards


.. note:: The series was implemented but eventually reverted due to some bug
          that was found late. It should be again merged in the next release,
          ie. 2024.1. That said, we kept the deprecation for the
          ``[ironic]\peer_list`` config option, which was explained below in
          `Config changes and Deprecations`_.


Problem description
===================

Nova's Ironic driver involves a single nova-compute service managing
many compute nodes, where each compute node record maps to an Ironic node.
Some deployments support 1000s of ironic nodes, but a single nova-compute
service is unable to manage 1000s of nodes and 1000s of instances.

Currently we support setting a partition key, where nova-compute only
cares about a subset of ironic nodes, those associated with a specific
conductor group. However, some conductor groups can be very large,
servered by many ironic-conductor services.

To help with this, Nova has attempted to dynamically spread ironic
nodes between a set of nova-compute peers. While this work some of
the time, there are some major limitations:

* when one nova-compute is down, only unassigned ironic nodes can
  move to another nova-compute service
* i.e. when one nova-compute is down, all ironic nodes with nova instances
  associated with the down nova-compute service are unable to be
  managed, i.e. reboot will fail
* moreover, when the old nova-compute comes back up, which might take
  some time, there are lots of bugs as the hash ring slowly rebalances.
  In part because every nova-compute fetches all nodes, in a large enough
  cloud, this can take over 24 hours.

This spec is about tweaking the way we shard Ironic compute nodes.
We need to stop violating deep assumptions in the compute manager
code by moving to a more static ironic node partitions.

Use Cases
---------

Any users of the ironic driver that have more than one
nova-compute service per conductor group should move to an
active-passive failover mode.

The new static sharding will be of paritcular interest for clouds
with ironic conductor groups that are greater than around
1000 baremetal nodes.

.. NOTE: many parts of this story work today but
 need better documentation:

 * understanding the current scale limit of around 500-1000 ironic
  nodes per nova-compute, and the best way to scale beyond that
 * sharding ironic-conductors and nova-computes using
  ironic conductor groups.
  Note: conductor groups have a specific use in Ironic
  and this is not it, but it works for some users.
 * active-passive failover for nova-compute services
  running the ironic driver.
  Note: the time to start up a new process after a
  failover is way too high, particularly at larger
  scales without conductor groups.

Proposed change
===============

We add a new configuration option:

* [ironic] shard_key

By default, there will be no shard_key set, and we will continue to
expose all ironic nodes from a single nova-compute process.
Mostly, this is to keep things simple for smaller deployments,
i.e. when you have less than 500 ironic nodes.

When the operator sets a shard_key, the compute-node process will
use the shard_key when querying a list of nodes in Ironic.
We must never try to list all Ironic nodes when
the Ironic shard key is defined in the config.

When we look up a specific ironic node via a node uuid or
instance uuid, we should not restrict that to either the shard key
or conductor group.

Similar to checking the instance uuid is still present on the Ironic
node before performing an action, or ensuring there is no instance uuid
before provisioning, we should also check the node is in the correct
shard (and conductor group) before doing anything with that Ironic node.

Config changes and Deprecations
-------------------------------

We will keep the option to target a specific conductor group,
but this option will be renamed from partition_key to conductor_group.
This is addative to the shard_key above, the target ironic nodes are
those in both the correct `shard_key` and the correct `conductor_group`,
when both are configured.

We will deprecate the use of the `peer_list`.
We should log a warning when the hash ring is being used,
i.e. when it has more than one member added to the hash ring.

In addtion, we need the logic that tries to move Compute Nodes
to never work unless the peer_list is larger than one. More details
in the data model impact section.

When deleting a ComputeNode object, we need to have the driver
confirm that is safe. In the case of Ironic we will check to see if
the configured Ironic has a node with that uuid, searching across all
conductor groups and all shard keys. When the ComputeNode object is not
deleted, we should not delete the entry in placement.

nova-manage move ironic node
----------------------------

We will create a new nova-manage command::

  nova-manage ironic-compute-node-move <ironic-node-uuid> \
      --service <destination-service>

This command will do the following:

* Find the ComputeNode object for this ironic-node-uuid
* Error if the ComputeNode type does not match the ironic driver.
* Find the related Service object for the above ComputeNode
  (i.e. the host)
* Error if the service object is not reported as down, and
  has not also been put into maintanance. We do not require
  forced down, because we might only be moving a subset of
  nodes associated with this nova-compute service.
* Check the Service object for the destination service host exists
* Find all non-deleted instances for this (host,node)
* Error if there is more than 1 non-deleted instance found.
  It is OK if we find zero or 1 instances.
* In one DB transaction:
  move the ComputeNode object to the destination service host and
  move the Instance (if there is one) to the destination service host

The above tool is expected to be used as part of this wider process
of migrating from the old peer_list to the new shard key. There are
two key scearios (although the tool may help operator recover from
other issues as well):

* moving from a peer_list to a single nova-compute
* moving from peer_list to shard_key, while keeping multiple nova-compute
  proccesses (for a single conductor group)

Migrate from peer_list to single nova-compute
---------------------------------------------

Small deployments (i.e. less than 500 ironic nodes)
are recommended to move from a peer_list of, for example,
three nova-compute services, to a single nova-compute service.
On failure of the nova-compute service, operators can either manually start
the processes on a new host, or use an automatic active-passive HA scheme.

The process would look something like this:

* ironic and nova both default to an empty_shard key by default,
  such that all ironic nodes are in the same default shard
* start a new nova-compute service running the ironic driver,
  ideally with a syntheic value for `[DEFAULT]host` e.g. `ironic`
  This will log warnings about the need to use the nova-compute
  migration tool before being able to manage any nodes
* stop all existing nova-compute services
* mark them as forced-down via the API
* Now loop around all ironic nodes and call this, assuming your
  nova-compute service has its host value of just `ironic`:
  `nova_manage ironic-compute-node-move <uuid> --service ironic`

The periodic tasks in the new nova-compute service will gradually
pick up the new ComputeNodes, and will start being able to recieve
commands such a reboot for all the moved instances.

While you could start the new nova-compute service after
having migrated all the ironic compute nodes, but that would
lead to higher downtime during the migration.

Migrate from peer_list to shard_key
-----------------------------------

The proccess to move from the hash key based peer_list to the static
shard_key from ironic is very similar to the above process:

* Set the shard_key on all your ironic nodes, such that you can spread
  the nodes out between your nova-compute processes,
* Start your new nova compute processes, one for each `shard_key`,
  possibly setting a synthetic `[DEFAULT]host` value that matches the
  `my_shard_key`.
* Shutdown all the older nova-compute processs with `[ironic]peer_list` set
* Mark those older services as in maintainance via the Nova API
* For each shard_key in Ironic, work out which service host you have mapped
  each one to above, then run this for each ironic node uuid in the shard:
  `nova_manage ironic-compute-node-move <uuid> --service my_shard_key`
* Delete the old services via the Nova API, now there are no instances
  or compute nodes on those services

While you could start the new nova-compute services after the migration,
that would lead to a slightly longer downtime.

Adding new compute nodes
------------------------

In general, there is no change when adding nodes into existing
shards.

Similarly, you can add a new nova-compute process for a new shard
and then start to fill that up with nodes.

Move an ironic node between shards
----------------------------------

When removing nodes from ironic at the end of their life, or
adding large numbers of new nodes, you may need to rebalance
the shards.

To move some ironic nodes, you need to move the nodes in
groups associated with a specific nova-compute process.
For each nova-compute and the associated ironic nodes you
want to move to a different shard you need to:

* Shutdown the affected nova-compute process
* Put nova-compute services into in maintanance
* In Ironic API update the shard key on the Ironic node
* Now move each ironic node to the correct new nova-compute
  process for the shard key it was moved into:
  `nova_manage ironic-compute-node-move <uuid> --service my_shard_key`
* Now unset maintanance mode for the nova-compute,
  and start that service back up

Move shards between nova-compute services
-----------------------------------------

To move a shard between nova-compute services, you need to
replace the nova-compute process with a new one:

* ensure the destination nova-compute is configured with the
  shard you want to move, and is running
* stop the nova-compute process currently serving the shard
* force-down the service via the API
* for each ironic node uuid in the shard call nova-manage
  to move it to the new nova-compute process

Alternatives
------------

We could require nova-compute processes to be explicitly forced down,
before allowing the nova-manage to move the ironic nodes about,
in a similar way to evacuate.
But this creates problems when trying to re-balance shards as you
remove nodes at the end of their life.

We could consider a list of shard keys, rather than a single shard key
per nova-compute. But for this first version, we have chosen the simpler
path, that appears to have few limitations.

We could attempt to keep fixing the hash ring recovery within the ironic
driver, but its very unclear what will break next due to all the deep
assumptions made about the nova-compute process. The specific assumptions
include:

* when nova-compute breaks, its usually the hypervisor hardware that
  has broken, which includes all the nova servers running on that.
* all locking and management of a nova server object is done by the
  currently assigned nova-compute node, and this is only ever changed
  by explict move operations like resize, migrate, live-migration
  and evacuate. As such we can use simple local locks to ensure
  concurrent operations don't conflict, along with DB state checking.

Data model impact
-----------------

A key thing we need to ensure is that ComputeNode objects are only
automatically moved between service objects when in legacy hash ring mode.
Currently, this only happens for unassigned ComputeNodes.

In this new explicit shard mode, only nova-manage is able to move
ComputeNode objects. In addtion, nova-manage will also move associated
instances. However, similar to evacuate, this will only be allowed
when the currently associated service is forced down.

Note, this applies when a nova-compute finds a ComputeNode that is should
own, but the Nova database says its already owned by a difference service.
In this scenario, we should log a warning to the operator
to ensure they have migrated that ComputeNode from its old location
before this nova-compute service is able to manage it.

In addition, we should ensure we only delete a ComputeNode object
when the driver explictly says its safe to delete. In the case of
the Ironic driver, we should ensure the node no longer exists in
Ironic, being sure to search across all shards.

This is all very related this spec on robustfying
the Compute Node and Service object relationship:
https://review.opendev.org/c/openstack/nova-specs/+/853837

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

Users will experience a more reliable Ironic and Nova integration.

Performance Impact
------------------

It should help users more easily support large ironic deployments
integrated with Nova.

Other deployer impact
---------------------

We will rename the "partition_key" configuration to be expliclity
"conductor_group".

We will deprecate the peer list key. When we start up and see
anything set, we ommit a warning about the bugs in using this
legacy auto sharding, and recomend moving to the explicit sharding.

There is a new `shard_key` config, as descirbed above.

There is a new nova_manage CLI command to move Ironic compute nodes
on forced-down nova-compute services to a new one.

Developer impact
----------------

None

Upgrade impact
--------------

For those currenly using peer_list, we need to document how they
can move to the new sharding approach.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  JayF

Other contributors:
  johnthetubaguy

Feature Liaison
---------------

Feature liaison: None

Work Items
----------

* rename conductor group partition key config
* deprecate peer_list config, with warning log messages
* add compute node move and delete protections, when peer_list not used
* add new shard_key config, limit ironic node list using shard_key
* add nova-manage tool to move ironic nodes between compute services
* document operational processes around above nova-manage tool

Dependencies
============

The deprecation of the peer list can happen right away.

But the new sharding depends on the Ironic shard key getting added:
https://review.opendev.org/c/openstack/ironic-specs/+/861803

Ideally we add this into Nova after robustify compute node has landed:
https://review.opendev.org/c/openstack/nova/+/842478

Testing
=======

We need some functional tests for the nova-manage command to ensure
all of the safty guards work as expected.

Documentation Impact
====================

A lot of docs needed for the Ironic driver on the operational
procedures around the shard_key.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.1 Antelope
     - Introduced
   * - 2023.2 Bobcat
     - Re-proposed
