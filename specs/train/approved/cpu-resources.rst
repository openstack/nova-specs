..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================
CPU resource tracking
=====================

https://blueprints.launchpad.net/nova/+spec/cpu-resources

We would like to both simplify the configuration of a compute node with regards
to CPU resource inventory as well as make the quantitative tracking of
dedicated CPU resources consistent with the tracking of shared CPU resources
via the placement API.

Problem description
===================

The ways that CPU resources are currently tracked in Nova is overly complex
and, due to the coupling of CPU pinning with NUMA-related concepts inside the
``InstanceNUMATopology`` and ``NUMATopology`` (host) objects, difficult to
reason about in terms that are consistent with other classes of resource in
nova.

Tracking of dedicated CPU resources is not done using the placement API,
therefore there is no way to view the physical processor usage in the system.
The CONF options and extra specs / image properties surrounding host CPU
inventory and guest CPU pinning are difficult to understand, and despite
efforts to document them, there are only a few individuals who even know how to
"properly" configure a compute node for hosting certain workloads.

We would like to both simplify the configuration of a compute node with regards
to CPU resource inventory as well as make the quantitative tracking of
dedicated CPU resources consistent with the tracking of shared CPU resources
via the placement API.

Definitions
-----------

**physical processor**
    A single logical processor on the host machine that is associated with a
    physical CPU core or hyperthread

**dedicated CPU**
    A physical processor that has been marked to be used for a single guest
    only

**shared CPU**
    A physical processor that has been marked to be used for multiple guests

**guest CPU**
    A logical processor configured in a guest

**VCPU**
    Resource class representing a unit of CPU resources for a single guest
    approximating the processing power of a single physical processor

**PCPU**
    Resource class representing an amount of dedicated CPUs for a single guest

**CPU pinning**
    The process of deciding which guest CPU should be assigned to which
    dedicated CPU

**pinset**
    A set of physical processors

**pinset string**
    A specially-encoded string that indicates a set of specific physical
    processors

**NUMA-configured host system**
    A host computer that has multiple physical processors arranged in a
    non-uniform memory access architecture.

**guest virtual NUMA topology**
    When a guest wants its CPU resources arranged in a specific non-uniform
    memory architecture layout. A guest's virtual NUMA topology may or may not
    match an underlying host system's physical NUMA topology.

**emulator thread**
    An operating system thread created by QEMU to perform certain maintenance
    activities on a guest VM

**I/O thread**
    An operating system thread created by QEMU to perform disk or network I/O
    on behalf of a guest VM

**vCPU thread**
    An operating system thread created by QEMU to execute CPU instructions on
    behalf of a guest VM

Use Cases
---------

As an NFV orchestration system, I want to be able to differentiate between CPU
resources that require stable performance and CPU resources that can tolerate
inconsistent performance

As an edge cloud deployer, I want to specify which physical processors should
be used for dedicated CPU and which should be used for shared CPU

As a VNF vendor, I wish to specify to the infrastructure whether my VNF can use
hyperthread siblings as dedicated CPUs

Proposed change
===============

Add ``PCPU`` resource class
---------------------------

In order to track dedicated CPU resources in the placement service, we need a
new resource class to differentiate guest CPU resources that are provided by a
host CPU that is shared among many guests (or many guest vCPU threads) from
guest CPU resources that are provided by a single host CPU.

A new ``PCPU`` resource class will be created for this purpose. It will
represent a unit of guest CPU resources that is provided by a dedicated host
CPU. In addition, a new config option, ``[compute] cpu_dedicated_set`` will be
added to track the host CPUs that will be allocated to the ``PCPU`` inventory.
This will complement the existing ``[compute] cpu_shared_set`` config option,
which will now be used to track the host CPUs that will be allocated to the
``VCPU`` inventory. These sets must be disjoint sets. If the two values are no
disjoint, we will fail to start with an error. If they are, any host CPUs not
included in the combined set will be considered reserved for the host.

The ``Flavor.vcpus`` field will continue to represent the combined number of
CPUs used by the instance, be they dedicated (``PCPU``) or shared (``VCPU``).
In addition, the ``cpu_allocation_ratio`` will apply only to ``VCPU`` resources
since overcommit for dedicated resources does not make sense.

.. note::

    This has significant implications for existing config options like
    ``vcpu_pin_set`` and ``[compute] cpu_shared_set``. These are discussed
    :ref:`below <cpu-resources_upgrade>`.

Add ``HW_CPU_HYPERTHREADING`` trait
-----------------------------------

Nova exposes hardware threads as individual "cores", meaning a host with, for
example, two Intel Xeon E5-2620 v3 CPUs will report 24 cores - 2 sockets * 6
cores * 2 threads. However, hardware threads aren't real CPUs as they share
share many components with each other. As a result, processes running on these
cores can suffer from contention. This can be problematic for workloads that
require no contention (think: real-time workloads).

We support a feature called "CPU thread policies", first added in `Mitaka`__,
which provides a way for users to control how these threads are used by
instances. One of the policies supported by this feature, ``isolate``, allows
users to mark thread sibling(s) for a given CPU as reserved, avoiding resource
contention at the expense of not being able to use these cores for any other
workload. However, on a typical x86-based platform with hyperthreading enabled,
this can result in an instance consuming 2x more cores than expected, based on
the value of ``Flavor.vcpus``. These untracked allocations cannot be supported
in a placement world as we need to know how many ``PCPU`` resources to request
at scheduling time, and we can't inflate this number (to account for the
hyperthread sibling) without being absolutely sure that *every single host* has
hyperthreading enabled. As a result, we need to provide another way to track
whether hosts have hyperthreading or not. To this end, we will add the new
``HW_CPU_HYPERTHREADING`` trait, which will be reported for hosts where
hyperthreading is detected.

.. note::

    The ``HW_CPU_HYPERTHREADING`` trait will need to be among the traits that
    the virt driver cannot always override, since the operator may want to
    indicate that a single NUMA node on a multi-NUMA-node host is meant for
    guests that tolerate hyperthread siblings as dedicated CPUs.

.. note::

    This has significant implications for the existing CPU thread policies
    feature. These are discussed :ref:`below <cpu-resources_upgrade>`.

__ https://specs.openstack.org/openstack/nova-specs/specs/mitaka/implemented/virt-driver-cpu-thread-pinning.html

Example host configuration
--------------------------

Consider a compute node with a total of 24 host physical CPU cores with
hyperthreading enabled. The operator wishes to reserve 1 physical CPU core and
its thread sibling for host processing (not for guest instance use).
Furthermore, the operator wishes to use 8 host physical CPU cores and their
thread siblings for dedicated guest CPU resources. The remaining 15 host
physical CPU cores and their thread siblings will be used for shared guest vCPU
usage, with an 8:1 allocation ratio for those physical processors used for
shared guest CPU resources.

The operator could configure ``nova.conf`` like so::

    [DEFAULT]
    cpu_allocation_ratio=8.0

    [compute]
    cpu_dedicated_set=2-17
    cpu_shared_set=18-47

The virt driver will construct a provider tree containing a single resource
provider representing the compute node and report inventory of ``PCPU`` and
``VCPU`` for this single provider accordingly::

    COMPUTE NODE provider
        PCPU:
            total: 16
            reserved: 0
            min_unit: 1
            max_unit: 16
            step_size: 1
            allocation_ratio: 1.0
        VCPU:
            total: 30
            reserved: 0
            min_unit: 1
            max_unit: 30
            step_size: 1
            allocation_ratio: 8.0

Example flavor configurations
-----------------------------

Consider the following example flavor/image configurations, in increasing order
of complexity.

1) A simple web application server workload requires a couple of CPU resources.
   The workload does not require any dedicated CPU resources::

       resources:VCPU=2

   For example::

       $ openstack flavor create --vcpus 2 ... example-1
       $ openstack flavor set --property resources:VCPU=2 example-1

   Alternatively, you can skip the explicit resource request and this will be
   provided by default. This is the current behavior::

       $ openstack flavor create --vcpus 2 ... example-1

2) A database server requires 8 CPU resources, and the workload needs dedicated
   CPU resources to minimize effects of other workloads hosted on the same
   hardware::

       resources:PCPU=8

   For example::

       $ openstack flavor create --vcpus 8 ... example-2
       $ openstack flavor set --property resources:PCPU=8 example-2

   Alternatively, you can skip the explicit resource request and use the legacy
   ``hw:cpu_policy`` flavor extra spec instead::

       $ openstack flavor create --vcpus 8 ... example-2
       $ openstack flavor set --property hw:cpu_policy=dedicated example-2

   In this legacy case, ``hw:cpu_policy`` acts as an alias for
   ``resources=PCPU:${flavor.vcpus}`` as discussed :ref:`later
   <cpu-resources_upgrade>`.

3) A virtual network function running a packet-core processing application
   requires 8 CPU resources. The VNF specifies that the dedicated CPUs it
   receives should **not** be hyperthread siblings (in other words, it wants
   full cores for its dedicated CPU resources)::

       resources:PCPU=8
       trait:HW_CPU_HYPERTHREADING=forbidden

   For example::

       $ openstack flavor create --vcpus 8 ... example-3
       $ openstack flavor set --property resources:VCPU=8 \
           --property trait:HW_CPU_HYPERTHREADING=forbidden example-3

   Alternatively, you can skip the explicit resource request and trait request
   and use the legacy ``hw:cpu_policy`` and ``hw:cpu_thread_policy`` flavor
   extra specs instead::

       $ openstack flavor create --vcpus 8 ... example-3
       $ openstack flavor set --property hw:cpu_policy=dedicated \
           --property hw:cpu_thread_policy=isolate example-3

   In this legacy case, ``hw:cpu_policy`` acts as an alias for
   ``resources=PCPU:${flavor.vcpus}`` and ``hw:cpu_thread_policy`` acts as an
   alias for ``required=!HW_CPU_HYPERTHREADING``, as discussed :ref:`later
   <cpu-resources_upgrade>`.

   .. note::

       The use of the legacy extra specs won't give the exact same behavior as
       previously as hosts that have hyperthreads will be excluded, rather than
       used but have their thread siblings isolated. This is unavoidable, as
       discussed :ref:`below <cpu-resources_upgrade>`.

.. note::

    It will not initially be possible to request both ``PCPU`` and ``VCPU`` in
    the same request. This functionality may be added later but such requests
    will be rejected until that happens.

.. note::

    You will note that the resource requests only include the total amount of
    ``PCPU`` and ``VCPU`` resources needed by an instance. It is entirely up to
    the ``nova.virt.hardware`` module to **pin** the guest CPUs to the host
    CPUs appropriately, doing things like taking NUMA affinity into account.
    The placement service will return those provider trees that match the
    required amount of requested PCPU resources. But placement does not do
    assignment of specific CPUs, only allocation of CPU resource amounts to
    particular providers of those resources.

Alternatives
------------

There's definitely going to be some confusion around ``Flavor.vcpus``
referring to both ``VCPU`` and ``PCPU`` resource classes. To avoid this, we
could call the ``PCPU`` resource class ``CPU_DEDICATED`` to more explicitly
indicate its purpose. However, we will continue to use the ``VCPU`` resource
class to represent shared CPU resources and ``PCPU`` seemed a better logical
counterpart to the existing ``VCPU`` resource class.

Another option is to call the ``PCPU`` resource class ``VCPU_DEDICATED``. This
doubles down on the idea that the term *vCPU* refers to an instance's CPUs (as
opposed to the host CPUs) but the name is clunky and it's still somewhat
confusing.

Data model impact
-----------------

The ``NUMATopology`` object will need to be updated to include
``cpu_shared_set`` and ``cpu_dedicated_set`` fields and to deprecate the
``cpu_set`` field.

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

This proposal should actually make the CPU resource tracking easier to reason
about and understand for end users by making the inventory of both shared and
dedicated CPU resources consistent.

Performance Impact
------------------

There should be a positive impact on performance due to the placement service
being able to perform a good portion of the work that the
``NUMATopologyFilter`` currently does. The ``NUMATopologyFilter`` would be
trimmed down to only handling questions about whether a particular thread
allocation policy (tolerance of hyperthreads) could be met by a compute node.
The number of ``HostInfo`` objects passed to the ``NUMATopologyFilter`` will
have already been reduced to only those hosts which have the required number of
dedicated and shared CPU resources.

Note that the ``NUMATopologyFilter`` will still need to contain the more
esoteric and complex logic surrounding CPU pinning and understanding NUMA node
CPU amounts before compute nodes are given the ability to represent NUMA nodes
as child resource providers in provider tree.

Other deployer impact
---------------------

Primarily, the impact on deployers will be documentation-related. Good
documentation needs to be provided that, like the above example flavor
configurations, shows operators what resources and traits extra specs to
configure in order to get a particular behavior and which configuration options
have changed.

Developer impact
----------------

None.

.. _cpu-resources_upgrade:

Upgrade impact
--------------

The upgrade impact of this feature is large and while we will endeavour to
minimize impacts to the end user, there will be some disruption. The various
impacts are described below. Before reading these, it may be worth reading the
following articles which describe the current behavior of nova in various
situations:

* `NUMA, CPU Pinning and 'vcpu_pin_set'
  <https://that.guru/blog/cpu-resources/>`__

Configuration options
~~~~~~~~~~~~~~~~~~~~~

We will deprecate the ``vcpu_pin_set`` config option in Train. If both the
``[compute] cpu_dedicated_set`` and ``[compute] cpu_shared_set`` config options
are set in Train, this option will be ignored entirely and ``[compute]
cpu_shared_set`` will be used in place of ``vcpu_pin_set`` to calculate the
amount of ``VCPU`` resources to report for each compute node. If the
``[compute] cpu_dedicated_set`` option is not set in Train, we will issue a
warning and fall back to using ``vcpu_pin_set`` as the set of host logical
processors to allocate for ``PCPU`` resources. These CPUs **will not** be
excluded from the list of host logical processors used to generate the
inventory of ``VCPU`` resources since ``vcpu_pin_set`` is useful for all
NUMA-based instances, not just those with pinned CPUs, and we therefore cannot
assume that these will be used exclusively by pinned instances. However, this
double reporting of inventory is not considered an issue as our long-standing
advice has been to use host aggregates to group pinned and unpinned instances.
As a result, we should not encounter the two types of instance on the same host
and either the ``VCPU`` or ``PCPU`` inventory will be unused. If host
aggregates are not used and both pinned and unpinned instances exist in the
cloud, the user will already be seeing overallocation issues: namely, unpinned
instances do not respect the pinning constraints of pinned instances and may
float across the cores that are supposed to be "dedicated" to the pinned
instances.

We will also deprecate the ``reserved_host_cpus`` config option in Train. If
both the ``[compute] cpu_dedicated_set`` and ``[compute] cpu_shared_set``
config options are set in Train, the value of the ``reserved_host_cpus`` config
option will be ignored and neither the ``VCPU`` nor ``PCPU`` inventories will
have a reserved value unless explicitly set via the placement API.

If the ``[compute] cpu_dedicated_set`` config option is not set, a warning will
be logged stating that ``reserved_host_cpus`` is deprecated and that the
operator should set both ``[compute] cpu_shared_set`` and ``[compute]
cpu_dedicated_set``.

The meaning of ``[compute] cpu_shared_set`` will change with this feature, from
being a list of host CPUs used for emulator threads to a list of host CPUs used
for both emulator threads and ``VCPU`` resources. Note that because this option
already exists, we can't rely on its presence to do things like ignore
``vcpu_pin_set``, as outlined previously, and must rely on ``[compute]
cpu_dedicated_set`` instead.

Finally, we will change documentation for the ``cpu_allocation_ratio`` config
option to make it abundantly clear that this option ONLY applies to ``VCPU``
and not ``PCPU`` resources

Flavor extra specs and image metadata properties
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We will alias the ``hw:cpu_policy`` flavor extra spec and ``hw_cpu_policy``
image metadata option to ``resources=(V|P)CPU:${flavor.vcpus}`` using a
scheduler prefilter. For flavors/images using the ``shared`` policy, we will
replace this with the ``resources=VCPU:${flavor.vcpus}`` extra spec, and for
flavors/images using the ``dedicated`` policy, we will replace this with the
``resources=PCPU:${flavor.vcpus}`` extra spec. Note that this is similar,
though not identical, to how we currently translate ``Flavour.vcpus`` into a
placement request for ``VCPU`` resources during scheduling.

In addition, we will alias the ``hw:cpu_thread_policy`` flavor extra spec and
``hw_cpu_thread_policy`` image metadata option to
``trait:HW_CPU_HYPERTHREADING`` using a scheduler prefilter. For flavors/images
using the ``isolate`` policy, we will replace this with
``trait:HW_CPU_HYPERTHREADING=forbidden``, and for flavors/images using the
``require`` policy, we will replace this with the
``trait:HW_CPU_HYPERTHREADING=required`` extra spec.

Placement inventory
~~~~~~~~~~~~~~~~~~~

For existing compute nodes that have guests which use dedicated CPUs, the virt
driver will need to move inventory of existing ``VCPU`` resources (which are
actually using dedicated host CPUs) to the new ``PCPU`` resource class.
Furthermore, existing allocations for guests on those compute nodes will need
to have their allocation records updated from the ``VCPU`` to ``PCPU`` resource
class.

In addition, for existing compute nodes that have guests which use dedicated
CPUs **and** the ``isolate`` CPU thread policy, the number of allocated
``PCPU`` resources may need to be increased to account for the additional CPUs
"reserved" by the host. On an x86 host with hyperthreading enabled, this will
result in a 2x the number of ``PCPU``\ s being reserved (N ``PCPU`` resources
for the instance itself and N ``PCPU`` allocated to avoid another instance
using them). This will be considered legacy behavior and won't be supported for
new instances.

Implementation
==============

Assignee(s)
-----------

Primary assignees:

* stephenfin
* tetsuro nakamura
* jaypipes
* cfriesen
* bauzas

Work Items
----------

* Create ``PCPU`` resource class

* Create ``[compute] cpu_dedicated_set`` and ``[compute] cpu_shared_set``
  options

* Modify virt code to calculate the set of host CPUs that will be used for
  dedicated and shared CPUs by using the above new config options

* Modify the code that creates the request group from the flavor's extra specs
  and image properties to construct a request for ``PCPU`` resources when the
  ``hw:cpu_policy=dedicated`` spec is found (smooth transition from legacy)

* Modify the code that currently looks at the
  ``hw:cpu_thread_policy=isolate|share`` extra spec / image property to add a
  ``required=HW_CPU_HYPERTHREADING`` or ``required=!HW_CPU_HYPERTHREADING`` to
  the request to placement

* Modify virt code to reshape resource allocations for instances with dedicated
  CPUs to consume ``PCPU`` resources instead of ``VCPU`` resources

Dependencies
============

None.

Testing
=======

Lots of functional testing for the various scenarios listed in the use cases
above will be required.

Documentation Impact
====================

* Docs for admin guide about configuring flavors for dedicated and shared CPU
  resources

* Docs for user guide explaining difference between shared and dedicated CPU
  resources

* Docs for how the operator can configure a single host to support guests that
  tolerate thread siblings as dedicated CPUs along with guests that cannot

References
==========

* `Support shared and dedicated VMs on same host`_
* `Support shared/dedicated vCPU in one instance`_
* `Emulator threads policy`_

.. _Support shared and dedicated VMS on same host: https://review.openstack.org/#/c/543805/
.. _Support shared/dedicated vCPU in one instance: https://review.openstack.org/#/c/545734/
.. _Emulator threads policy: https://review.openstack.org/#/c/511188/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Originally proposed, not accepted
   * - Stein
     - Proposed again, not accepted
   * - Train
     - Proposed again
