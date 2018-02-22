..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Complex Anti-Affinity Policies
================================

https://blueprints.launchpad.net/nova/+spec/complex-anti-affinity-policies

This blueprint proposes to enable users to define the rules on policy to
meet more advanced policy requirement, also proposes to implement an example
that adding the ``max_server_per_host`` rule for ``anti-affinity`` policy.

Problem description
===================

Nova supports filtering and weighting to make informed decisions on where
a new instance should be created, and the ServerGroupAntiAffinityFilter
implements anti-affinity for a server group based on this scheduler
mechanism.

Users set the policy for the specific server group to enable the
anti-affinity for the server group. This meets the most basic requirement of
server group affinity, but it isn't enough for the more complex anti-affinity
requirement.

For example, users want to enable anti-affinity policy with a limit other
than 1, which is the static limit today. By doing this, the number of VMs in
the same anti-affinity group per host can be limited by users. To achieve both
the anti-affinity and resource utilization requirement, it's a very useful
ability to users, especially, when the users don't have enough hosts in their
cloud but still want some level of high reliability of their applications. In
addition, we also can't use the soft-anti-affinity policy since that is
implemented based on weights rather than host filtering.

So, the scheduler needs to provide some mechanism to enable users to define
the rules on policy to meet more advanced policy requirement.


Use Cases
---------

As a NFV user, in consideration of reliability and resource utilization, I
want a mechanism to add the limit on the instances max number per host in the
same anti-affinity group.

Proposed change
===============
This spec proposes to:

* Add a generic "rules" field which is a dict, can be applied to the policies.

  Now, only ``max_server_per_host`` for ``anti-affinity`` policy would be
  supported, the example usage as below:

  "max_server_per_host" rule for ``anti-affinity`` policy means that add
  the max limit on the number of VMs in a group on a given host. For
  example, if the user have a group of 6 instances and 2 hosts with a
  ``anti-affinity`` policy, it will be rejected in current anti-affinity
  policy, then the user can specify ``{'max_server_per_host': 3}`` rule for
  this group, and it means 6 instances get spread across 2 hosts and each
  host has 3 servers.

* Create a new API microversion to support these changes:

  1) Support passing a optional argument ``rules`` to the create instance
     group API. Now, we only support the "max_server_per_host" rule for
     ``anti-affinity`` policy as a optional entry with an int value >= 1
     which are validated with the json schema in API.

  2) The responses of ``POST /os-server-groups``, ``GET /os-server-groups``
     and ``GET /os-server-groups/{server_group_id}`` also need to be changed
     to the new policy format.

  3) Remove the empty and unused ``metadata`` field in the response of
     ``POST /os-server-groups``, ``GET /os-server-groups`` and
     ``GET /os-server-groups/{server_group_id}``.

* Change the ``ServerGroupAntiAffinityFilter`` to adapt to complex policy
  model.

  The filter will get the max_server_per_host limit from policy rules, and
  compare it against the number of servers within the same group on a given
  host. If the filter finds the number is not satisfied with the limit,
  it will filter out this host.

  The default ``max_server_per_host`` for the anti-affinity filter is 1 for
  backward compatibility.

Alternatives
------------

An alternative would be to have a setting for the max spread before the
scheduler would consider doubling up. The user can define how much redundancy
they want at a minimum regardless of how many instances are in the group.

Data model impact
-----------------

* The ``Text`` column ``rules`` will be added to the ``instance_group_policy``
  database table. A database schema migration will also be added in order to
  add the column.

  The format of the ``rules`` is a dict containing multiple key/value pairs
  like::

    {'max_server_per_host': 3, `other_key`: `other_value`}

* Add a new ``InstanceGroupPolicy`` versioned object including the ``policy``,
  ``rules`` and ``group_id`` fields.

* Add a new ``policy`` field to the ``InstanceGroup`` object.

  The InstanceGroup.policy would be an instance of ``InstanceGroupPolicy``,
  and the original ``policies`` field would be deprecated.

REST API impact
---------------

Following changes will be introduced in a new API microversion.

* POST /os-server-groups

  Support passing ``rules`` to the create instance group API and change the
  schema of creating server group to avoid creating a server with no policies.

  Example Create Server Group JSON request::

    {
        "server_group": {
            "name": "test",
            "policy": {
                "name": "anti-affinity",
                "rules": {
                    "max_server_per_host": 3
                }
            }
        }
    }

  The new JSON schema for the ``POST /os-server-groups`` as below::

    create = {
    'type': 'object',
    'properties': {
        'server_group': {
            'type': 'object',
            'properties': {
                'name': parameter_types.name,
                'policy':
                    {
                        'oneOf': [
                        {
                            'type': 'object',
                            'properties': {
                                'name': {
                                    'type': 'string',
                                    'enum': ['anti-affinity'],
                                },
                                'rules': {
                                    'type': 'object',
                                    'properties': {
                                        'max_server_per_host': parameter_types.positive_integer,
                                    },
                                    'additionalProperties': False
                                }
                            },
                            'required': ['name'],
                            'additionalProperties': False
                        },
                        {
                            'type': 'object',
                            'properties': {
                                'name': {
                                    'type': 'string',
                                    'enum': ['affinity', 'soft-anti-affinity', 'soft-affinity'],
                                },
                            },
                            'required': ['name'],
                            'additionalProperties': False
                        }]
                }
            },
            'required': ['name', 'policy'],
            'additionalProperties': False,
        }},
        'required': ['server_group'],
        'additionalProperties': False,
    }

  Change the response to the new policy format and remove the empty and unused
  ``metadata`` field::

    {
        "server_group": {
            "id": "5bbcc3c4-1da2-4437-a48a-66f15b1b13f9",
            "name": "test",
            "policy": {
                "name": "anti-affinity",
                "rules": {
                    "max_server_per_host": 3
                }
            }
            "members": []
        }
    }

  Note that: if the user creates a group without specifying the policy rules,
  the value of ``rules`` key is ``{}``.

* GET /os-server-groups

  Change the response to the new policy format and remove the empty and unused
  ``metadata`` field::

    {
        "server_groups": [
            {
                "id": "616fb98f-46ca-475e-917e-2563e5a8cd19",
                "name": "test",
                "policy": {
                    "name": "anti-affinity",
                    "rules": {
                        "max_server_per_host": 3
                    }
                },
                "members": [],
                "project_id": "6f70656e737461636b20342065766572",
                "user_id": "fake"
            }
        ]
    }

* GET /os-server-groups/{server_group_id}

  Change the response to the new policy format and remove the empty and unused
  ``metadata`` field::

    {
        "server_group": {
            "id": "5bbcc3c4-1da2-4437-a48a-66f15b1b13f9",
            "name": "test",
            "policy": {
                "name": "anti-affinity",
                "rules": {
                    "max_server_per_host": 3
                }
            },
            "members": []
        }
    }

Security impact
---------------

None

Notifications impact
--------------------

The ``server_group.create``, ``server_group.delete`` and
``server_group.add_member`` versioned notifications will be updated to include
the new ``policy`` field instead of the old ``policies`` field.

Other end user impact
---------------------

* python-novaclient will be modified to add this new ``rule`` param to the
  `nova server-group-create` shell command.
* python-openstackclient will be modified to add this new ``rule`` param to the
  `openstack server group create` shell command.


Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Yikun Jiang

Work Items
----------

* Add the ``rules`` attribute to the ``InstanceGroupPolicy`` data model.
* Create a new API microversion to support passing ``rules`` to the create
  instance group API.
* Modify the Nova client to handle the new microversion.
* Change the ``ServerGroupAntiAffinityFilter`` to adapt to new policy
  model.
* Change the ``_validate_instance_group_policy`` [1]_ in the after resource
  tracker claim to adapt to new policy model

Dependencies
============

None

Testing
=======

Would need new in-tree functional and unit tests.

Documentation Impact
====================

Docs needed for new API microversion and usage.

References
==========

 .. [1] Fix anti-affinity race condition on boot:
    https://review.openstack.org/#/c/77800/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Proposed
