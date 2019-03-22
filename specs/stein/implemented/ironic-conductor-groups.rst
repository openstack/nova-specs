..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================================
Use conductor groups to partition nova-compute services for Ironic
==================================================================

https://blueprints.launchpad.net/nova/+spec/ironic-conductor-groups

Use ironic's conductor group feature to limit the subset of nodes which a
nova-compute service will manage. This allows for partitioning nova-compute
services to a particular location (building, aisle, rack, etc), and provides a
way for operators to manage the failure domain of a given nova-compute service.

Problem description
===================

As OpenStack deployments become larger, and edge compute becomes a reality,
there is a desire to be able to co-locate the nova-compute service with
some subset of ironic nodes.

There is also a desire to be able to reduce the failure domain of a
nova-compute service, and to be able to make the failure domain more
predictable in terms of which ironic nodes can no longer be scheduled to.

Use Cases
---------

Operators managing large and/or distributed ironic environments need more
control over the failure domain of a nova-compute service.

Proposed change
===============

A configuration option ``partition_key`` will be added, to tell the
nova-compute service which ``conductor_group`` (an ironic-ism) it is
responsible for managing. This will be used as a filter when querying the list
of nodes from ironic, so that only the subset of nodes which have a
``conductor_group`` matching the ``partition_key`` will be returned.

As nova-compute services have a hash ring which further partitions the subset
of nodes which a given nova-compute service is managing, we need a mechanism to
tell the service which other compute services are managing the same
``partition_key``. To do this, we will add another configuration option,
``peer_list``, which is a comma-separated list of hostnames of other compute
services managing the same subset of nodes. If set, this will be used instead
of the current code, which fetches a list of all compute services running the
ironic driver from the database. To ensure that the hash ring splits nodes only
between currently running compute services, we will check this list against the
database and filter out any inactive services (i.e. has not checked in
recently) listed in ``peer_list``.

``partition_key`` will default to ``None``. If the value is ``None``, this
functionality will be disabled, and the behavior will be the same as before,
where all nodes are eligible to be managed by the compute service, and all
compute services are considered as peers. Any other value will enable this
service, limiting the nodes to the conductor group matching ``partition_key``,
and using the ``peer_list`` configuration option to determine the list of
peers.

Both options will be added to the ``[ironic]`` config group, and will be
"mutable", meaning it only requires a SIGHUP to update the running service with
new config values.

Alternatives
------------

Ideally, we wouldn't need a ``peer_list`` configuration option, as we would be
able to dynamically fetch this list from the database, and it's prone to
operator mistakes.

One option to do this is to add a field to the compute service record, to store
the partition key. Compute services running the ironic driver could then use
this field to determine their peer list. During the Stein PTG discussion
about this feature, we agreed not to do this, as adding fields or blobjects
in the service record for a single driver is a layer violation.

Another option is for the ironic driver to manage its own list of live services
in something like etcd, and the peer list could be determined from here. This
also feels like a layer violation, and requiring an etcd cluster only for a
particular driver feels confusing at best from an operator POV.

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

Using this feature slightly improves the performance of the resource tracker
update. Instead of iterating over the list of *all* ironic nodes to determine
which should be managed, the compute service will iterate over a subset of
ironic nodes.

Other deployer impact
---------------------

The two configuration options mentioned above are added, but are optional.
The feature isn't enabled unless ``partition_key`` is set.

It's worth noting what happens when a node's conductor group changes. If the
node has an instance, it continues being managed by the compute service
responsible for the instance, as we do today with rebalancing the hash ring.
Without an instance, the node will be picked up by a compute service managing
the new group at the next resource tracker run after the conductor group
changes.

Developer impact
----------------

None.

Upgrade impact
--------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jroll

Work Items
----------

* Add the configuration options and the new code paths.

* Add functional tests to ensure that the compute services manage the correct
  subset of nodes when this is enabled.

* Add documentation for deployers and operators.


Dependencies
============

None.


Testing
=======

This will need to be tested in functional tests, as it would require spinning
up at least three nova-compute services to properly test the feature. While
possible in integration tests, this isn't a great use of CI resources.


Documentation Impact
====================

Deployer and operator documentation will need updates.

References
==========

This feature and its implementation was roughly agreed upon during the Stein
PTG. See line 662 or so (at the time of this writing):
https://etherpad.openstack.org/p/nova-ptg-stein


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
