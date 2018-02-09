..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Support Traits in Allocation Candidates
=======================================

https://blueprints.launchpad.net/nova/+spec/add-trait-support-in-allocation-candidates

The placement API already supports filtering resource providers that have
capacity for a requested amount of resources. In addition to those quantitative
aspects of the request, the placement API also needs to filter out resource
providers that do not have a set of required qualitative attributes.

Problem description
===================

The `GET /allocation_candidates` only supports querying by quantitative aspect
with `resources` query parameters. For the qualitative aspect, we need an
additional parameter, `required`.

Use Cases
---------

This is an API proposal for the internal interaction between Nova and
Placement. The final use-case is the end user wants to boot up instance on the
compute node which has AVX cpu feature, the compute node doesn't have AVX cpu
feature will be filtered out even though they have the capacity.

Proposed change
===============

Proposes to add `required` query parameter to the `GET /allocation_candidates`
API. It will accept a list of traits, and the API will return a set of
allocation requests, the resource providers in those allocation request have
each of the traits in the parameter `required`.

With nested resource providers, traits defined on a parent RP are assumed to
belong to all its child (descendant) RPs. However, traits defined on a child
RP do not apply to the parent (ancestor) RPs. There is no implied sharing of
traits within aggregates.

Alternatives
------------

There also a proposal about `preferred_traits` parameter, it means nice to
have a list of traits. But there still haven't clear use-case for it, so it
isn't in the proposal.

Data model impact
-----------------

None

REST API impact
---------------

Proposals to add `required` parameter to the `GET /allocation_candidates`. It
accepts a list of traits separated by `,`. For example::

    GET /allocation_candidates?resources=VCPU:8,MEMORY_MB:1024,DISK_GB:4096&required=HW_CPU_X86_AVX,STORAGE_DISK_SSD

In the above request, the traits `HW_CPU_X86_AVX` and `STORAGE_DISK_SSD` are
required.

The validation for the `required` are:

* The `required` is optional, but `resources` is required parameter. So the
  `required` should be specified with specifiying `resources`.
* Any invalid traits in the `required` parameters will result in a
  `HTTPBadRequest 400`. Invalid trait means the trait isn't in the `os-traits`
  library and also isn't a custom trait defined by traits API.
* An empty value in `required` is not acceptable and will also result in a
  `HTTPBadRequest 400`.

The API will return a set of allocation requests, each allocation request is
a combination of root resource provider, nested resource providers and shared
resource providers. The required traits may spread in those resource providers.

For example, the compute node resource provider might have the `HW_CPU_X86_AVX`
trait but not the `STORAGE_DISK_SSD` trait. That trait may be associated with
the shared storage provider that is providing the DISK_GB resources for the
request. For the above request, the API will return an allocation request
which includes two resource providers, compute node resource provider provides
`VCPU` and `MEMORY_MB` resources with trait `HW_CPU_X86_AVX`, the shared
storage provider are sharing `DISK_GB` resource with trait `STORAGE_DISK_GB`.

All traits which the resource provider have will be included in the provider
summary of the responses::

  {
    "allocation_requests": [
        {
            "allocations": [
                {
                    "resource_provider": {
                        "uuid": "88a5187d-e0a4-426d-bed4-54e7e89b2adb"
                    },
                    "resources": {
                        "VCPU": 8,
                        "MEMORY_MB": 1024,
                    }
                },
                {
                    "resource_provider": {
                        "uuid": "0d684632-eca3-40a9-ab6b-b7457227143c"
                    },
                    "resources": {
                        "DISK_GB": 4096
                    }
                }
            ]
        }
    ],
    "provider_summaries": {
        "88a5187d-e0a4-426d-bed4-54e7e89b2adb": {
            "resources": {
                "VCPU": {
                    "capacity": 128,
                    "used": 1
                }
                "MEMORY_MB": {
                    "capacity": 8096,
                    "used": 0
                }
            },
            "traits": [
                "HW_CPU_X86_SSE",
                "HW_CPU_X86_SSE2",
                "HW_CPU_X86_AVX",
                "HW_CPU_X86_AVX2",
                ...
            ]
        },
        "0d684632-eca3-40a9-ab6b-b7457227143c": {
            "resources": {
                "DISK_GB": {
                    "capacity": 40960,
                    "used": 0
                }
            },
            "traits": [
                "STORAGE_DISK_SSD"
            ]
        }
    }
  }

When there are no traits for a resource provider, the `traits` attribute is
still in the response, and with a empty list.

All the above change are in a new microversion.

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

In the implementation, there will be a separate SQL to query the resource
providers which have required traits. Then filter those resource providers
in the main SQL. It will be slower than single SQL, but it is acceptable.

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
  Alex Xu <hejie.xu@intel.com>

Other contributors:
  Lei Zhang <lei.a.zhang@intel.com>

Work Items
----------

* Add a common method to query the resource providers which have required
  traits.
* Integrate the common query method into the main query.
* Fill the traits into the ProviderSummaries object.
* Expose the `required` parameter in the `GET /allocation_candidates` API with
  a new microversion.

Dependencies
============

None

Testing
=======

DB and API functional tests are required.

Documentation Impact
====================

The placement API reference should be updated with the new parameters.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
