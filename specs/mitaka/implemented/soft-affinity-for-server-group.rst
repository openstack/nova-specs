..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Add soft affinity support for server group
==========================================

https://blueprints.launchpad.net/nova/+spec/soft-affinity-for-server-group

As a tenant I would like to schedule instances on the same host if possible,
so that I can achieve collocation. However if it is not possible to schedule
some instance to the same host then I still want that the subsequent
instances are scheduled together on another host. In this way I can express
a good-to-have relationship between a group of instances.

As a tenant I would like to schedule instances on different hosts if possible.
However if it is not possible I still want my instances to be scheduled even
if it means that some of them are placed on the same host.


Problem description
===================

Use Cases
---------

End User might want to have a less strict affinity and anti-affinity
rule than what is today available in server-group API extension.
With the proposed good-to-have affinity rule the End User can request nova
to schedule the instance to the same host (i.e. stack them) if possible.
However if it is not possible (e.g. due to resource limitations) then End User
still wants to keep the instances on a small amount of different host.

With the proposed good-to-have anti-affinity rule the End User can request
nova to spread the instances in the same group as much as possible.

Proposed change
===============

This change would extend the existing server-group API extension with two new
policies soft-affinity and soft-anti-affinity.

When a instance is booted into a group with soft-affinity policy the scheduler
will use a new weight AffinityWeight to sort the available hosts according to
the number of instances running on them from the same server-group in a
descending order.

When an instance is booted into a group with soft-anti-affinity policy the
scheduler will use a new weight AntiAffinityWeight to sort the available hosts
according to the number of instances running on them from the same
server-group in a ascending order.

The two new weights will get the necessary information about the number of
instances per host through the weight_properties (filter_properties) in
a similar way as the GroupAntiAffinityFilter gets the list of hosts used by
a group via the filter_properties.

These new soft-affinity and soft-anti-affinity policies are mutually exclusive
with each other and with the other existing server-group policies. This means
that a server group cannot be created with more than one policy as every
combination of the existing policies (affinity, anti-affinity, soft-affinity,
soft-anti-affinity) are contradicting.

If the scheduler sees a request which requires any of the new weigher classes
but those classes are not configured then the scheduler will reject the request
with an exception similarly to the case when affinity policy is requested but
ServerGroupAffinityFilter is not configured.

Alternatives
------------

Alternatively End User can use the server-group with affinity policy and if
the instance cannot be scheduled because the host associated to the group is
full then End User can create a new server-group for the subsequent instances.
However with large amount of instances that occupy many hosts this manual
process can become quite cumbersome.

Data model impact
-----------------

No schema change is needed.

There will be two new possible values soft-affinity and soft-anti-affinity for
the policy column of the instance_group_policy table.

REST API impact
---------------

POST: v2/{tenant-id}/os-server-groups
  The value of the policy request parameter can be soft-affinity and
  soft-anti-affinity as well. So the new JSON schema will be the following::

    {"type": "object",
     "properties": {
        "server_group": {
            "type": "object",
            "properties": {
                "name": parameter_types.name,
                "policies": {
                    "type": "array",
                    "items": [{"enum": ["anti-affinity", "affinity",
                                        "soft-anti-affinity",
                                        "soft-affinity"]}],
                    "uniqueItems": True,
                    "additionalItems": False}},
                "required": ["name", "policies"],
                "additionalProperties": False}},
        "required": ["server_group"],
        "additionalProperties": False}


  For example the following POST request body will be valid::

    {"server_group": {
        "name": "test",
        "policies": [
            "soft-anti-affinity"]}}

  And will be answered with the following response body::

    {"server_group": {
        "id": "5bbcc3c4-1da2-4437-a48a-66f15b1b13f9",
        "name": "test",
        "policies": [
            "soft-anti-affinity"
        ],
        "members": [],
        "metadata": {}}}

The above API change will be introduced in a new API microversion.

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

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  balazs-gibizer


Work Items
----------

* Add two new weighers to the filter scheduler. These weights will
  sort the available hosts by the number of instances from the same
  server-group.
* Update FilterScheduler to reject the request if the new policy is
  requested but the related weigher is not configured.
* Update the server-group API extension to allow soft-affinity and
  soft-anti-affinity as the policy of a group.


Dependencies
============

None

Testing
=======

Unit test coverage will be provided.

The following functional test coverage will be provided:

* create groups with soft-affinity and soft-anti-affinity
* boot two servers with soft-affinity with enough resource on the same host.
  Nova shall boot both server to the same host.
* boot two servers with soft-affinity but there is not enough resource to boot
  the second server to the same host as the first server. Nova shall boot the
  second server to a different host.
* boot two servers with soft-anti-affinity and two compute hosts are available
  with enough resources. Nova shall boot the two servers to two separate hosts.
* boot two servers with soft-anti-affinity but only a single compute host is
  available. Nova shall boot the two servers to the same host.
* Rebuild, migrate, evacuate server with soft-affinity
* Rebuild, migrate, evacuate server with soft-anti-affinity

Documentation Impact
====================

New weights need to be described in filter_scheduler.rst.


References
==========

* instance-group-api-extension BP
  https://blueprints.launchpad.net/nova/+spec/instance-group-api-extension
* Group API wiki
  https://wiki.openstack.org/wiki/GroupApiExtension
