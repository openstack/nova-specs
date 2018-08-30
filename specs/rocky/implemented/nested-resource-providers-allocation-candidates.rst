..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Nested Resource Providers - Allocation Candidates
=================================================

https://blueprints.launchpad.net/nova/+spec/nested-resource-providers-allocation-candidates

Nested resource providers functionality was added to nova and placement in the
Queens and Pike releases, however there remain a numer of pieces of
functionality that need to be completed for the feature to be wholly useful.
One of these pieces is the full integration of nested resource providers in the
allocation requests returned by the ``GET /allocation_candidates`` HTTP
endpoint in the placement service.

Problem description
===================

With the `update_provider_tree`_ work, the resource tracker and virt drivers
are now capable of constructing a tree of nested resource providers, each
decorated with various traits and containing inventory records of various
resource classes.

.. _update_provider_tree: https://review.openstack.org/#/c/540111/

While this is critical to properly represent the hierarchical relationship of
child providers to parent providers, this hierarchical structure is still not
used in calculating the set of allocation requests returned to nova scheduler
during pre-filtering compute hosts.

The placement service needs to consider a provider's membership within a tree
in determining whether a provider can supply the resources in a particular
request.

Consider the following arrangement, with a compute node that has some VCPU and
MEMORY_MB inventory as well as two SR-IOV physical functions with inventory of
SR-IOV virtual functions. Only one of those physical functions is decorated
with a trait representing different a type of offload::

                             compute node  -- VCPU: 16, MEMORY_MB: 16384
                             /           \
                            /             \
                       NUMA NODE 0    NUMA NODE 1
                           |              |
                           |              |
      SRIOV_NET_VF:4 --  PF 0           PF 1 -- SRIOV_NET_VF:4
                                                HW_NIC_OFFLOAD_GRO

If we request 2 ``VCPU`` and 1 ``SRIOV_NET_VF`` resource, we would expect to
get back 2 allocation requests, with each allocation request containing the
compute node resource provider for the ``VCPU`` resources and one of the
physical function resource providers for the ``SRIOV_NET_VF`` resource.

However, currently, we will get 0 results back from ``GET
/allocation_candidates``.  Similarly, if we request 2 ``VCPU`` and 1
``SRIOV_NET_VF`` along with ``HW_NIC_OFFLOAD_GRO`` as a required trait, we
would expect to get back 1 allocation request containing the PF which has the
required trait.  However, we currently get 0 results since the calculation of
allocation candidates is not "nested aware".

Use Cases
---------

None

Proposed change
===============

Update the ``AllocationCandidates.get_by_requests()`` method so that it
understands that when provider trees are present, a resource may be provided by
a child provider. When evaluating required traits, the placement service must
ensure that traits are associated with the providers that are actually
supplying the inventory to meet the allocation request.

Namely, with the host described in `Problem description`_,

.. code::

    GET /allocation_candidates?resources=VCPU:2,SRIOV_NET_VF=1

would provide the following result:

.. code-block:: javascript

    {
        "allocation_requests": [
            {
                "allocations": {
                    "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                        "resources": {
                            "VCPU": 2
                        },
                    },
                    "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                        "resources": {
                            "SRIOV_NET_VF": 1
                        },
                    },
                },
            },
            {
                "allocations": {
                    "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                        "resources": {
                            "VCPU": 2
                        },
                    },
                    "99c09379-6e52-4ef8-9a95-b9ce6f68452e": {
                        "resources": {
                            "SRIOV_NET_VF": 1
                        },
                    },
                },
            },
        ],
        "provider_summaries": {
            "35791f28-fb45-4717-9ea9-435b3ef7c3b3": {
                "resources": {
                    "VCPU": {
                        "used": 0,
                        "capacity": 16
                    },
                "traits": []
                },
            },
            "7d2590ae-fb85-4080-9306-058b4c915e3f": {
                "resources": {
                    "SRIOV_NET_VF": {
                        "used": 0,
                        "capacity": 4
                    },
                "traits": []
                },
            },
            "99c09379-6e52-4ef8-9a95-b9ce6f68452e": {
                "resources": {
                    "SRIOV_NET_VF": {
                        "used": 0,
                        "capacity": 4
                    },
                },
                "traits": [
                    "HW_NIC_OFFLOAD_GRO"
                ]
            },
        },
    }

Note that in ``provider_summaries`` we will show only resource providers that
are in ``allocation_requests``.

We'd also like to adapt the placement service to return all providers in a
particular provider tree that match the search criteria in
``provider_summaries``. This is sequentially enabled by another spec,
`Return resources of entire trees in Placement`_.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

Introduce a new microversion to signal that provider trees are now properly
handled in the return of ``GET /allocation_candidates``.

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

It's going to be slower to evaluate allocation candidates when provider trees
are present. There's just no way around this.

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
  jaypipes

Work Items
----------

* Add a function to retrieve provider trees that meet a set of requested
  resource amounts and required traits
* Integrate the function into the ``AllocationCandidates.get_by_requests()``
  method and add a microversion to signal the new behavior

Dependencies
============

None

Testing
=======

Lots of functional tests required for various levels of nesting

Documentation Impact
====================

Would be good to be super-clear about the behaviour of the placement service
when evaluating a request for resources and traits when nested resource
providers are present in the system.

References
==========

* `Return resources of entire trees in Placement`_ spec

.. _`Return resources of entire trees in Placement`: https://blueprints.launchpad.net/nova/+spec/placement-return-all-resources
