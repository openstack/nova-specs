..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Return resources of entire trees in Placement
=============================================

https://blueprints.launchpad.net/nova/+spec/placement-return-all-resources

This spec aims to extend the placement ``GET /allocation_candidates``
API to include all resources in trees in ``provider_summaries`` field of
the response body.

Problem description
===================

The response of ``GET /allocation_candidates`` API provides two fields of
``allocation_requests`` and ``provider_summaries``. The callers, like the
filter scheduler in nova, would use information in ``provider_summaries``
in sorting or filtering providers to allocate consumers.

However, ``provider_summaries`` doesn't contain information of resource
providers that are not in the ``allocation_request`` field. This would
be a problem when a compute host resource provider doesn't have resource
inventories but its children, NUMA resource providers, can provide the
resources. (See the `NUMA Topology with Resource Providers`_ spec)

Case1: The compute node doesn't have any resources itself
---------------------------------------------------------

For example, let's consider a host which has several resources for each
NUMA node.

.. code::

                        +-----------------+
                        | <CN_NAME>       |
                        +-----------------+
                        /                 \
     +------------------+                 +-----------------+
     | <NUMA_NODE_0>    |                 | <NUMA_NODE_1>   |
     | PCPU: 8          |                 | PCPU: 8         | (dedicated CPUs)
     | MEMORY_MB: 4096  |                 | MEMORY_MB: 4096 |
     +------------------+                 +-----------------+
              |
    +--------------------+
    | <PHYS_FUNC_PCI_ID> |
    | SRIOV_NET_VF: 8    |
    +--------------------+

Case2: The compute node doesn't have requested resources itself
---------------------------------------------------------------

Similary, we can consider a host which has VCPU inventories for its
resource class, and has PCPU inventories for its children, NUMA
resource providers.

.. code::

                        +-----------------+
                        | <CN_NAME>       |
                        | VCPU: 8         | (shared CPUs)
                        +-----------------+
                        /                 \
     +------------------+                 +-----------------+
     | <NUMA_NODE_0>    |                 | <NUMA_NODE_1>   |
     | PCPU: 8          |                 | PCPU: 8         | (dedicated CPUs)
     | MEMORY_MB: 4096  |                 | MEMORY_MB: 4096 |
     +------------------+                 +-----------------+
              |
    +--------------------+
    | <PHYS_FUNC_PCI_ID> |
    | SRIOV_NET_VF: 8    |
    +--------------------+


If a user requests 4 PCPUs and 2048 MEMORY_MB for each NUMA node, under
`Granular Resource Request Syntax`_ spec, nova would issue the following
request to placement;

.. code::

    GET /allocation_candidates?resources1=PCPU:4,MEMORY_MB=2048
                              &resources2=PCPU:4,MEMORY_MB=2048
                              &group_policy=isolate

In both cases, case1 and case2, nova would get the following json response,
where there are NUMA resource providers but no compute host resource provider.

.. code-block:: javascript

    {
        "allocation_requests": [
            {
                "allocations": {
                    "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                        "resources": {
                            "PCPU": 4,
                            "MEMORY_MB":2048
                        },
                    },
                    "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                        "resources": {
                            "PCPU": 4,
                            "MEMORY_MB":2048
                        },
                    },
                },
            },
        ],
        "provider_summaries": {
            "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                "resources": {
                    "PCPU": {
                        "used": 0,
                        "capacity": 8
                    },
                    "MEMORY_MB": {
                        "used": 0,
                        "capacity": 6144
                    }
                },
                "traits": []
            },
            "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                "resources": {
                    "PCPU": {
                        "used": 0,
                        "capacity": 8
                    },
                    "MEMORY_MB": {
                        "used": 0,
                        "capacity": 6144
                    }
                },
                "traits": []
            }
        }
    }

This is because placement currently has following logics.

1. In the ``provider_summaries``, we don't show up resource providers that are
   not in the ``allocation_requests``. In both case1 and case2, this blocks
   letting compute nodes appear.

2. In the ``provider_summaries``, we don't show up resource providers that
   have no resource inventories. In case1, this blocks letting the compute
   node appear.

3. In the ``provider_summaries``, we don't show up resource classes that are
   not requested. In case2, this blocks letting the compute node appear.

From this response, there is no way where nova scheduler knows these resource
providers are compute hosts or their children. This would be a problem
because nova scheduler need to subsequently pass the candidate hosts to nova
internal filters and weighers.

Use Cases
---------

As an NFV operator, I'd like to enable NUMA aware resource management in
Placement.

Proposed change
===============

0. Return all nested providers in tree
--------------------------------------

At first, we need to change ``GET /allocation_candidates`` to include
resource providers in ``provider_summaries`` that aren't in
``allocation_requests`` when those other resource providers are in
the same provider tree.
Also, we add new fields of ``root_provider_uuid`` and ``parent_provider_uuid``
for each resource provider to expose the hierarchy.

This requirement is necessary for both case1 and case2.

1. Return resource providers without inventories
------------------------------------------------

We additionally need to change codes to include resource providers
without inventories in ``provider_summaries``. This would let operators
to get the following response for case1, where the compute node has no
inventory.

.. code-block:: javascript

    {
        "allocation_requests": [
            {
                "allocations": {
                    "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                        "resources": {
                            "PCPU": 4,
                            "MEMORY_MB":2048
                        },
                    },
                    "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                        "resources": {
                            "PCPU": 4,
                            "MEMORY_MB":2048
                        },
                    },
                },
            },
            {
                "allocations": {
                    "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                        "resources": {
                            "PCPU": 8,
                            "MEMORY_MB":4096
                        },
                    },
                },
            },
            {
                "allocations": {
                    "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                        "resources": {
                            "PCPU": 8,
                            "MEMORY_MB":4096
                        },
                    },
                },
            },
        ],
        "provider_summaries": {
            "99c09379-6e52-4ef8-9a95-b9ce6f68452e": {
                "resources": {},
                "traits": [],
                "parent_provider_uuid": "",
                "root_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
            },
            "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                "resources": {
                    "PCPU": {
                        "used": 0,
                        "capacity": 8
                    },
                    "MEMORY_MB": {
                        "used": 0,
                        "capacity": 6144
                    },
                },
                "traits": [],
                "parent_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
                "root_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e"
            },
            "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                "resources": {
                    "PCPU": {
                        "used": 0,
                        "capacity": 8
                    },
                    "MEMORY_MB": {
                        "used": 0,
                        "capacity": 6144
                    },
                },
                "traits": [],
                "parent_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
                "root_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
            },
            "542df8ed-9be2-49b9-b4db-6d3183ff8ec8": {
                "resources": {
                    "SRIOV_NET_VF": {
                        "used": 0,
                        "capacity": 16
                    },
                },
                "traits": [],
                "parent_provider_uuid": "7d2590ae-fb85-4080-9306-058b4c915e3f",
                "root_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
            },
        },
    }


2. Return all resources in ``provider_summaries``
-------------------------------------------------

Also, we additionally need to change codes to include resource providers
with unrequested inventories in ``provider_summaries``. This would let
operators get the following response in case2, where the compute node has 8
VCPU inventories, which is not requested.

.. code-block:: javascript

    {
        "allocation_requests": [
            {
                "allocations": {
                    "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                        "resources": {
                            "PCPU": 4,
                            "MEMORY_MB":2048
                        },
                    },
                    "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                        "resources": {
                            "PCPU": 4,
                            "MEMORY_MB":2048
                        },
                    },
                },
            },
            {
                "allocations": {
                    "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                        "resources": {
                            "PCPU": 8,
                            "MEMORY_MB":4096
                        },
                    },
                },
            },
            {
                "allocations": {
                    "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                        "resources": {
                            "PCPU": 8,
                            "MEMORY_MB":4096
                        },
                    },
                },
            },
        ],
        "provider_summaries": {
            "99c09379-6e52-4ef8-9a95-b9ce6f68452e": {
                "resources": {
                    "VCPU": {
                        "used": 0,
                        "capacity": 8
                    },
                },
                "traits": [],
                "parent_provider_uuid": "",
                "root_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
            },
            "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                "resources": {
                    "PCPU": {
                        "used": 0,
                        "capacity": 8
                    },
                    "MEMORY_MB": {
                        "used": 0,
                        "capacity": 6144
                    },
                },
                "traits": [],
                "parent_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
                "root_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e"
            },
            "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                "resources": {
                    "PCPU": {
                        "used": 0,
                        "capacity": 8
                    },
                    "MEMORY_MB": {
                        "used": 0,
                        "capacity": 6144
                    },
                },
                "traits": [],
                "parent_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
                "root_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
            },
            "542df8ed-9be2-49b9-b4db-6d3183ff8ec8": {
                "resources": {
                    "SRIOV_NET_VF": {
                        "used": 0,
                        "capacity": 16
                    },
                },
                "traits": [],
                "parent_provider_uuid": "7d2590ae-fb85-4080-9306-058b4c915e3f",
                "root_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
            },
        },
    }

Accordingly, the nova scheduler is changed to be aware of the hierarchy and
to find out compute hosts to be passed to internal filters and weighers.

Alternatives
------------

We can just add ``root_provider_uuid`` field in ``provider_summaries``
instead of exposing the whole tree. For both cases, case1 and case2,
the response would be:

.. code-block:: javascript

    {
        "allocation_requests": [
            {
                "allocations": {
                    "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                        "resources": {
                            "PCPU": 4,
                            "MEMORY_MB":2048
                        },
                    },
                    "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                        "resources": {
                            "PCPU": 4,
                            "MEMORY_MB":2048
                        },
                    },
                },
            },
            {
                "allocations": {
                    "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                        "resources": {
                            "PCPU": 8,
                            "MEMORY_MB":4096
                        },
                    },
                },
            },
            {
                "allocations": {
                    "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                        "resources": {
                            "PCPU": 8,
                            "MEMORY_MB":4096
                        },
                    },
                },
            },
        ],
        "provider_summaries": {
            "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                "resources": {
                    "PCPU": {
                        "used": 0,
                        "capacity": 8
                    },
                    "MEMORY_MB": {
                        "used": 0,
                        "capacity": 6144
                    }
                },
                "traits": [],
                "parent_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
                "root_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
            },
            "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                "resources": {
                    "PCPU": {
                        "used": 0,
                        "capacity": 8
                    },
                    "MEMORY_MB": {
                        "used": 0,
                        "capacity": 6144
                    }
                },
                "traits": [],
                "parent_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
                "root_provider_uuid": "99c09379-6e52-4ef8-9a95-b9ce6f68452e",
            },
        },
    }


However, putting all the resources in trees enables further weighing and
filtering in the following use cases for example.

As a user deploying an instance with VCPU, MEMORY_MB, and DISK_GB, I don't
want to deploy this instance to hosts with VGPU or SRIOV_NET_VF to save the
resources for instances that need the devices.

Building the weighers or filters in nova is out of the scope of this spec,
but it is good to prepare for these use cases in placement using this
opportunity.

Another alternative is doing nothing in placement and change the nova
scheduler to issue additional queries to placement to get the whole tree
information.

.. code::

    GET /resource_providers?in_tree={uuid}

But querying a request for each resource provider candidate is not efficient.

Data model impact
-----------------

None

REST API impact
---------------

With a new microversion, ``GET /allocation_candidates`` will include all
the resource providers in trees with new fields of ``root_provider_uuid``
and ``parent_provider_uuid`` as described in `Proposed change`_ section.

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

It's going to be slower to evaluate allocation candidates since it's going
to be building much more data to send back to the client.
There's just no way around this, so in implementation we should at least take
care not to increase the numbers of SQL queries to enable this feature.

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
  Tetsuro Nakamura (tetsuro)

Work Items
----------

* Change codes to include all the providers in trees in
  ``provider_summaries``. Namely, we need following changes to the current
  behavior.

    * Include resource providers of entire tree in ``provider_summaries`` even
      if a resource provider is not in the ``allocation_requests``. - See the
      `Return all nested providers in tree`_ patch for details.

    * Include information on all their resource classes in
      ``provider_summaries`` even if a resource class is not in the requested
      resources. - See the `Return all resources in provider_summaries`_ patch
      for details.

    * Include resource providers in ``provider_summaries`` even if a
      resource provider doesn't have any inventories - See the
      `Return resource providers without inventories`_ patch for details.

* Add fields of ``root_provider_uuid``, ``parent_provider_uuid`` in
  ``provider_summaries`` with a new microversion.

* Change the nova scheduler to be aware of the hierarchy and to
  find out the root provider to be passed to the internal filters and
  weighers.

Dependencies
============

This spec depends on `Nested Resource Providers - Allocation Candidates`_
spec.

Testing
=======

Provide new gabbi tests as well as unit tests.

Documentation Impact
====================

The new behavior with the new microversion should be well described
in the release note and in the `Placement api-ref document`_.
The `Microversion history document`_ will be also updated.


References
==========

* `NUMA Topology with Resource Providers`_ spec
* `Granular Resource Request Syntax`_ spec
* `Nested Resource Providers - Allocation Candidates`_ spec
* `Placement api-ref document`_
* `Microversion history document`_

.. _`NUMA Topology with Resource Providers`: https://review.openstack.org/#/c/552924/
.. _`Granular Resource Request Syntax`: https://specs.openstack.org/openstack/nova-specs/specs/rocky/approved/granular-resource-requests.html
.. _`Nested Resource Providers - Allocation Candidates`: https://specs.openstack.org/openstack/nova-specs/specs/rocky/approved/nested-resource-providers-allocation-candidates.html
.. _`Placement api-ref document`: https://developer.openstack.org/api-ref/placement/
.. _`Microversion history document`: https://docs.openstack.org/nova/latest/user/placement.html#rest-api-version-history
.. _`Return all nested providers in tree`: https://review.openstack.org/#/c/559480/
.. _`Return all resources in provider_summaries`: https://review.openstack.org/#/c/558045/
.. _`Return resource providers without inventories`: https://review.openstack.org/#/c/559554/
