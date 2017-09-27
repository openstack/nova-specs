..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Placement Allocation Requests
=============================

https://blueprints.launchpad.net/nova/+spec/placement-allocation-requests

We propose to have the placement API return to the scheduler a set of
alternative allocation choices that the scheduler may then use to both make a
fitness decision as well as attempt a claim of resources on multiple complex
resource providers.

Problem description
===================

Nova's scheduler will soon be claiming resources by sending a `POST
/allocations/{consumer_uuid}` request to the Placement API after selecting a
target compute host. The Nova scheduler constructs the claim request for only a
single resource provider at the moment: the provider representing the target
compute host that it selected. Only claiming against a single resource provider
is problematic; as we move to representing more and more complex resource
provider relationships (nested providers and providers of shared resources), we
want the Nova scheduler to be able to claim resources against these nested or
sharing resource providers.

In order for this to happen, we propose creating a new REST API endpoint in the
Placement API called `GET /allocation_requests` that will return a collection
of opaque (to the Nova compute node and conductor) HTTP request bodies that can
be provided to a `POST /allocations/{consumer_uuid}` request along with a set
of information the Nova scheduler can use to make fitness choices for the
launch requests.

Use Cases
---------

This is an internal blueprint/spec, not intended to implement for any
particular use case but rather simplify and structure the communication between
the Nova scheduler and the Placement API.

Proposed change
===============

We propose adding a new `GET /allocation_requests` REST API endpoint that will
return both a collection of opaque request bodies that can be sent to the `POST
/allocations/{consumer_uuid}` endpoint as well as a collection of information
that the scheduler can use to determine best fit for an instance launch
request.

.. note:: At this time, we make no suggestion as to **how** the scheduler will
          use the information returned back from the placement API in its
          fitness decision. It may choose to replace the information that it
          currently uses from the cell databases with information from the
          placement API, or it could choose to merge the information somehow.
          That piece is left for future discussion.

The scheduler shall then proceed to choose an appropriate destination host for
a build request (or more than one destination host if the
`RequestSpec.num_instances` is greater than 1). However, instead of immediately
returning this destination host, the scheduler will now work with the placement
API to claim resources on the chosen host **before** sending its decision back
to the conductor.

The scheduler will claim resources against the destination host by choosing an
allocation request that contains the UUID of the destination host and calling
the placement API's `POST /allocations/{consumer_uuid}` call, passing in the
allocation request as the body of the HTTP request along with the user and
project ID of the instance.

If the attempt to claim resources fails due to a concurrent update (a condition
that is normal and expected in environments with heavy load), the scheduler
will retry the claim request several times and then, if still unable to claim
resources against the initially-selected destination host, will move to the
next host in its list of weighed hosts for the request.

Alternatives
------------

There were a number of alternative approaches considered by the team.

Alternative 1 was to have the Placement API transparently claim resources on
more than one provider. The scheduler would pick the primary resource provider
(compute node), attempt to `POST /allocations/{consumer_uuid}` to claim
resources against that compute node, and the placement API would write
allocation records for resources against *that* compute node resource provider
as well as sharing resource providers (e.g. in the case of a shared storage
pool) and child providers (e.g. consuming SRIOV_NET_VF resources from a
particular SRIOV physical function child provider). While this alternative
would shield from the Nova scheduler implementation details about sharing
providers and nested provider hierarchies, the Placement API is not well-suited
to make decisions about things like packing/spreading strategies or picking a
particular SRIOV PF for a target network function workload. Instead, the Nova
scheduler is responsible for sorting the list of providers it receives from the
Placement API that meet resource and trait requirements and choosing which
providers to allocate against.

Alternative 2 was to modify the existing `GET /resource_providers` Placement
REST API endpoint to return information about sharing providers and child
providers and have the scheduler reporting client contain the necessary logic
to build provider hierarchies, determine which sharing provider is associated
with which providers, and essentially re-build a representation of usage and
inventory records in memory. This alternative kept the Placement API free of
much complex logic but came at the cost of dramatically changing the returned
response from an established REST API endpoint and making the usage of that
REST API endpoint inconsistent depending on the caller.

Data model impact
-----------------

None.

REST API impact
---------------

The new `GET /allocation_requests` Placement REST API endpoint shall accept
requests with the following query parameters:

* `resources`: A comma-delimited string of `RESOURCE_CLASS:AMOUNT` pairs, one
  for each class of resource requested. Example:
  `?resources=VCPU:1,MEMORY_MB:1024,DISK_GB:100`

Given an HTTP request of:

`GET /allocation_requests?resources=$RESOURCES`

where `$RESOURCES` = "VCPU:4,MEMORY_MB:16384,DISK_GB:100" and given two empty
compute nodes each attached via an aggregate to a resource provider sharing
`DISK_GB` resources, the following would be the HTTP response returned by the
placement API::

    {
        "allocation_requests": [
            {
                "allocations": [
                    {
                        "resource_provider": {
                            "uuid": $COMPUTE_NODE1_UUID
                        },
                        "resources": {
                            "VCPU": $AMOUNT_REQUESTED_VCPU,
                            "MEMORY_MB": $AMOUNT_REQUESTED_MEMORY_MB
                        }
                    },
                    {
                        "resource_provider": {
                            "uuid": $SHARED_STORAGE_UUID
                        },
                        "resources": {
                            "DISK_GB": $AMOUNT_REQUESTED_DISK_GB
                        }
                    },
                ],
            },
            {
                "allocations": [
                    {
                        "resource_provider": {
                            "uuid": $COMPUTE_NODE2_UUID
                        },
                        "resources": {
                            "VCPU": $AMOUNT_REQUESTED_VCPU,
                            "MEMORY_MB": $AMOUNT_REQUESTED_MEMORY_MB
                        }
                    },
                    {
                        "resource_provider": {
                            "uuid": $SHARED_STORAGE_UUID
                        },
                        "resources": {
                            "DISK_GB": $AMOUNT_REQUESTED_DISK_GB
                        }
                    },
                ],
            },
        ],
        "provider_summaries": {
            $COMPUTE_NODE1_UUID: {
                "resources": {
                    "VCPU": {
                        "capacity": 120,   # NOTE, this represents the total - reserved * allocation_ratio
                        "used": 4,
                    },
                    "MEMORY_MB": {
                        "capacity": 1024,
                        "used": 48,
                    }
                }
            },
            $COMPUTE_NODE2_UUID: {
                "resources": {
                    "VCPU": {
                        "capacity": 120,
                        "used": 4,
                    },
                    "MEMORY_MB": {
                        "capacity": 1024,
                        "used": 48,
                    }
                }
            },
            $SHARED_STORAGE_UUID: {
                "resources": {
                    "DISK_GB": {
                        "capacity": 2000,
                        "used": 100,
                    }
                }
            }
        }
    ]

Note that we are not dealing with either nested resource providers or traits in
the above. Those concepts will be added to the response in future patches.

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

Returning a list of allocation requests that all meet the Nova scheduler's
request for resources/traits and allowing the Nova scheduler to iterate over
these allocation requests, retrying them if a concurrent claim happens, should
actually increase the throughput of the Nova scheduler by reducing the amount
of time between resource constraint retries.

Other deployer impact
---------------------

The Placement service will need to be upgraded before the nova-scheduler
service.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

jaypipes

Work Items
----------

#. Implement the API logic in the Placement service with a new microversion.
#. Update the FilterScheduler driver to use the new Placement API.

Dependencies
============

* https://blueprints.launchpad.net/nova/+spec/shared-resources-pike

  Partially completed in Pike.

Testing
=======

Unit and in-tree functional tests. Integration testing will be covered by
existing Tempest testing.

Documentation Impact
====================

There should be good devref documentation written that describes in more
explicit detail what the placement service is responsible for and what the Nova
scheduler is responsible for, and how this new API call will be used to shared
information between placement and Nova scheduler.

References
==========

* Original straw-man proposal was developed on etherpad:

  http://etherpad.openstack.org/p/placement-allocations-straw-man

* Spec for claiming resources in the scheduler:

  https://specs.openstack.org/openstack/nova-specs/specs/pike/approved/placement-claims.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
