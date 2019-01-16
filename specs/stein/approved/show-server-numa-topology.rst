..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Show server numa topology
=========================

Add NUMA into new sub-resource ``GET /servers/{server_id}/topology`` API.

https://blueprints.launchpad.net/nova/+spec/show-server-numa-topology

Problem description
===================

There is server-related NUMA information that is useful to both end user
and Admin but currently there is no available API to retrieve that information.

The APIs ``GET /servers`` and ``GET /servers/{id}`` can list extra specs which
may contain some hints about the guest numa topology but it is not easy to
interpret.


Use Cases
---------

* The admin wants to see the topology (RAM, CPU) without logging in to the
  guest VM.

* The admin wants a unified way to get topology information, independent of
  how the various gest OSes expose it.

* The admin wants to know the virtual-to-physical mapping for one or more
  instances for the purpose of debugging, and admin need make sure the NUMA
  topology is what it's supposed to be, and is correctly mapped onto Host.

* The end user could have all of above abilities if admin alows them by change
  policy rule.


Proposed change
===============

In nova, NUMA topology contains group of related properties, like the amount
of memory managed by a NUMA cell, the list of memory page sizes supported on
the NUMA cell,the vCPU thread to logical host processor mapping, and the cpu
thread policy. This spec proposes an API to present all this NUMA information,
including the virtual-to-physical mapping.

This spec proposes a new sub-resource 'topology' to servers API:

``GET /servers/{server_id}/topology``

This API is admin only by default, it could be exposed to users/roles by
changing the default policy rule.

API returns each cell's information belonging to one server, including socket,
cpu, thread, mem, page size, cpuset, CPU pinned info, siblings, thread policy,
CPU pinning, host NUMA node number.

If there is no NUMA information available, the corresponding key's value
will simply be set to None.

Alternatives
------------

Instead of put these information into ``GET /servers/{server_id}/topology``,
there are other 2 options:

* add NUMA information into existed sub-resource ``diagnostics``:
  ``GET /servers/{server_id}/diagnostics``
  returns the NUMA information for one server. As NUMA toplogy does not change
  for given server, it's better put under new ``topology`` sub-resource.

* put the NUMA information under ``GET /servers/{id}`` and
  ``GET /servers/detail``.
  This would negatively affect performance as it needs an additional database
  query (via the ``InstanceNUMATopology`` object's ``get_by_instance_uuid``
  method).

Data model impact
-----------------

None


REST API impact
---------------

API ``GET /servers/{server_id}/topology`` will show NUMA information with
a new microversion.

The returned information for NUMA topology::

   {
         # overall policy: TOPOLOGY % 'index
         "nodes":[
                    {
                      # Host Numa Node
                      # control by policy TOPOLOGY % 'index:host_info'
                      "host_numa_node": 3,
                      # 0:5 means vcpu 0 pinning to pcpu 5
                      # control by policy TOPOLOGY % 'index:host_info'
                      "cpu_pinning": {0:5, 1:6},
                      "vcpu_set": [0,1,2,3],
                      "siblings": [[0,1],[2,3]],
                      "memory_mb": 1024,
                      "pagesize_kb": 4096,
                      "sockets": 1,
                      "cores": 2,
                      # one core has at least one thread
                      "threads": 2
                    }
                    ...
                   ], # nodes

        "cpu_thread_policy": "prefer"

    }


Security impact
---------------

* These information exposed by this API is admin only by default, and fine
  control policy ``TOPOLOGY % 'index:host_info'`` use to keep host only
  information to admin while this API expose to end user.

* Add new ``topology`` policy, admin only by default:

  .. code-block:: python

    TOPOLOGY = 'os_compute_api:servers:topology:%s'

    server_topology_policies = [
        policy.DocumentedRuleDefault(
            BASE_POLICY_NAME,
            base.RULE_ADMIN_API,
            "Show the topology data for a server",
            [
                {
                    'method': 'GET',
                    'path': '/servers/{server_id}/topology'
                }
            ]),
        policy.DocumentedRuleDefault(
            # control host numa node and cpu pin information
            TOPOLOGY % 'index:host_info',
            base.RULE_ADMIN_API,
            "List all servers with detailed information",
            [
                {
                    'method': 'GET',
                    'path': '/servers/{server_id}/topology'
                }
            ]),
    ]


Notifications impact
--------------------

N/A

Other end user impact
---------------------

* python novaclient and python-openstackclient would display numa_topology
  information.

Performance Impact
------------------

None

Other deployer impact
---------------------

N/A

Developer impact
----------------

N/A

Upgrade impact
--------------

N/A


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Yongli He


Work Items
----------

* Add new microversion for this change.


Dependencies
============

N/A

Testing
=======

* Add functional api_sample tests.

Documentation Impact
====================

The API document should be changed to introduce this new feature.

References
==========

* Stein PTG discussion:https://etherpad.openstack.org/p/nova-ptg-stein

* Mailing list discussion:
  http://lists.openstack.org/pipermail/openstack-discuss/2018-December/001070.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Version
   * - Stein
     - First Introduced

