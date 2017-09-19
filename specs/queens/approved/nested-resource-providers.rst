..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Nested Resource Providers
=========================

https://blueprints.launchpad.net/nova/+spec/nested-resource-providers

We propose changing the database schema, object model and REST API of resource
providers to allow a hierarchical relationship among different resource
providers to be represented.

Problem description
===================

With the addition of the new placement API, we now have a new way to account
for quantitative resources in the system. Resource providers contain
inventories of various resource classes. These inventories are simple integer
amounts and, along with the concept of allocation records, are designed to
answer the questions:

* "how many of a type of resource does this provider have available?"
* "how much of a type of resource is being consumed in the system?"
* "what level of over-commit does each provider expose for each type of
  resource?"

In the initial version of the resource provider schema in the placement API, we
stuck with a simple world-view that resource providers could be related to each
other only via an aggregate relationship. In other words, a resource provider
"X" may provide shared resources to a set of other resource providers "S" if
and only if "X" was associated with an aggregate "A" that all members of "S"
were also associated with.

This relationship works perfectly fine for things like shared storage or IP
pools. However, certain classes of resource require a more parent->child
relationship than a many-to-many relationship that the aggregate association
offers. Two examples of where a parent->child relationship is more appropriate
are when handling VCPU/MEMORY_MB resources on NUMA nodes on a compute host and
when handling SRIOV_NET_VF resources for NICs on a compute host.

In the case of NUMA nodes, the system must be able to track how many VCPU and
MEMORY_MB have been allocated from each individual NUMA node on the host.
Allocating memory to a guest and having that memory span address space across
two banks of DIMMs attached to different NUMA nodes results in sub-optimal
performance, and for certain high-performance guest workloads this penalty is
not acceptable.

Another example is the SRIOV_NET_VF resource class, which is provided by
SRIOV-enabled network interface cards. In the case of multiple SRIOV-enabled
NICs on a compute host, different qualitative traits may be tagged to each NIC.
For example, the NIC called enp2s0 might have a trait "CUSTOM_PHYSNET_PUBLIC"
indicating that the NIC is attached to a physical network called "public". The
NIC enp2s1 might have a trait "CUSTOM_PHYSNET_PRIVATE" that indicates the NIC
is attached to the physical network called "Intranet". We need a way of
representing that these NICs each provide SRIOV_NET_VF resources but those
virtual functions are associated with different physical networks. In the
resource providers data modeling, the entity which is associated with
qualitative traits is the **resource provider** object. Therefore, we require a
way of representing that the SRIOV-enabled NICs are themselves resource
providers with inventories of SRIOV_NET_VF resources. Those resource providers
are contained on a compute host which is a resource provider that has inventory
records for *other* types of resources such as VCPU, MEMORY_MB or DISK_GB.

This spec proposes that nested resource providers be created to allow for
distinguishing details of complex components of some resource providers. During
review the question came up about "rolling up" amounts of these nested
providers to the root level. Imagine this scenario: I have a NIC with two PFs,
each of which has only 1 VF available, and I get a request for 2 VFs without
any traits to distinguish them. Since there is no single resource provider that
can satisfy this request, it will not select this root provider, even though
the root provider "owns" 2 VFs. This spec does not propose any sort of "rolling
up" of inventory, but this may be something to consider in the future. If it is
an idea that has support, another BP/spec can be created then to add this
behavior.

Use Cases
---------

As an NFV cloud operator, I wish to request that my VNF workload needs an SRIOV
virtual function on a NIC that is tagged to the physical network "public" and I
want to be able to view the resource consumption of SRIOV virtual functions on
a per-physical-network basis.

As an NFV cloud operator, I wish to ensure that the memory and vCPU assigned to
my workload is local to a particular NUMA topology and that those resources are
represented in unique inventories per NUMA node and reported as separate
allocations.

Proposed change
===============

We will add two new attributes to the resource provider data model:

* `parent_provider_uuid`: Indicates the UUID of the immediate parent provider.
  This will be None for the vast majority of providers, and for nested resource
  providers, this will most likely be the compute host's UUID. To be clear,
  a resource provider can have 0 or 1 parents. We will not support multiple
  parents for a resource provider.
* `root_provider_uuid`: Indicates the UUID of the resource provider that is at
  the "root" of the tree of providers. This field allows us to implement
  efficient tree-access queries and avoid use of recursive queries to follow
  child->parent relations.

A new microversion will be added to the placement REST API that adds the above
attributes to the appropriate request and response payloads.

The scheduler reporting client shall be modified to track NUMA nodes and
SRIOV-enabled NICs as child resource providers to a parent compute host
resource provider.

The `VCPU` and `MEMORY_MB` resource classes will continue to be inventoried on
the parent resource provider (i.e the compute node resource provider) and not
the NUMA node child providers. The NUMA node child providers will have
inventory records populated for the `NUMA_CORE`, `NUMA_THREAD` and
`NUMA_MEMORY_MB` resource classes. When a boot request is received, the Nova
API service will need to determine whether the request (flavor and image)
specifies a particular NUMA topology and, if so, construct the request to the
placement service for the appropriate `NUMA_XXX` resources. This is currently
out of scope for this spec. This spec is only about the inventorying of the
various child providers with appropriate resource classes.

On the CPU-pinning side of the equation, we do not plan to allow a compute node
to serve as *either* a general-purpose compute node *or* as a target for
NUMA-specific (pinned) workloads. A compute node will be either a target for
pinned workloads or it will be a target for generic (floating CPU) workloads.
It is not yet clear what we will use to indicate that a compute node targets
floating workloads or not. Initial thoughts were to use the
pci_passthrough_whitelist CONF option to determine this however this still
needs to be debated.

This spec will simply ensure that if a virt driver returns a NUMATopology
object in the result of its get_available_resource() call, then we will create
child resource providers representing those NUMA nodes. Similarly, if the PCI
device manager returns a set of SR-IOV physical functions on the compute host,
we will create child resource provider records for those SR-IOV PFs.

Alternatives
------------

We could try hiding the `root_provider_uuid` attribute from the GET
/resource-provider[s] REST API response payload to reduce complexity of the
API. We will still, however, need a REST API call that "gets all resource
providers in a tree" where the user would pass a UUID and we'd look up all
resource providers having that UUID as their root provider UUID.

Instead of having a concept of nested resource providers, we could force
deployers to create custom resource classes for every permutation of physical
network trait. For instance, assuming the example above, the operator would
need to create an SRIOV_NET_VF_PUBLIC_NET and a SRIOV_NET_VF_INTRANET_NET
custom resource class and then manually set the inventory of the compute node
resource provider to an amount of VFs each PF exposed. The problem with this
approach is two-fold. First, we no longer have any standardization on the
SRIOV_NET_VF resource class. Secondly, we are coupling the qualitative and
quantitative aspects of a provider together again, which is part of the problem
with the existing Nova codebase and why it has been hard to standardize the
tracking and scheduling of resources in the first place.

Data model impact
-----------------

Two new fields will be added to the `resource_providers` DB table:

* `root_provider_uuid`: This will be populated using an online data migration
  that sets `root_provider_uuid` to the value of the `resource_providers.uuid`
  field for all existing resource providers.
* `parent_provider_uuid`: This will be a NULLable field and default to NULL

REST API impact
---------------

`root_provider_uuid` and `parent_provider_uuid` fields will be added to the
corresponding request and response payloads of appropriate placement REST APIs.

The `GET /resource_providers` call will get a new filter on `root={uuid}` that,
when present, will return all resource provider records, inclusive of the root,
having a `root_provider_uuid` equal to `{uuid}`.

The filter parameter `root={uuid}` will *not* be added to
`GET /allocation_candidates`, as this call is for a specific use case for the
Nova scheduler, and there is no use case for it.

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

None.

Other deployer impact
---------------------

None. The setting and getting of provider tree information will be entirely
handled in the `nova-compute` worker with no changes needed by the deployer.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jaypipes

Other contributors:
  cdent

Work Items
----------

* Add DB schema and object model changes
* Add REST API microversion adding new attributes for resource providers and
  allocation candidates
* Add REST API microversion adding new `root={uuid}` filter on `GET
  /resource_providers`
* Add code in scheduler reporting client to track NUMA nodes as child resource
  providers on the parent compute host resource provider
* Add code in scheduler reporting client to track SRIOV PFs as child resource
  providers on the parent compute host resource provider

Please note that not all of this spec is expected to be implemented in a single
release cycle. At the Queens PTG we agreed that fully suppporting NUMA will
probably have to be deferred to the next release.

Dependencies
============

None.

Testing
=======

Most of the focus will be on functional tests for the DB/server and the REST
API with new functional tests added for the specific NUMA and SRIOV PF child
provider scenarios described in this spec.

Documentation Impact
====================

Some devref content should be written.

References
==========

http://etherpad.openstack.org/p/nested-resource-providers

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
   * - Pike
     - Re-proposed
   * - Queens
     - Re-proposed
