..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
NUMA Topology with Resource Providers
=====================================

https://blueprints.launchpad.net/nova/+spec/numa-topology-with-rps

Now that `Nested Resource Providers`_ is a thing in both Placement API and
Nova compute nodes, we could use the Resource Providers tree for explaining
the relationship between a root Resource Provider (root RP) ie. a compute node,
and one or more Non-Uniform Memory Access (NUMA) nodes (aka. cells), each of
them having separate resources, like memory or PCI devices.

.. note::

  This spec only targets to model resource capabilities for NUMA nodes in some
  general and quite abstract manner. We won't address in this spec how we
  should model NUMA-affinized hardware like PCI devices or GPUs and will
  discuss these relationships in a later spec.


Problem description
===================

The NUMATopologyFilter checks a number of resources, including emulator threads
policies, CPU pinned instances and memory page sizes. Additionally, it does two
different verifications :

- *whether* some host can fit the query because it has enough capacity

- *which* resource(s) should be used for this query (eg. which pCPUs or NUMA
  node)


With NUMA topologies modeled as Placement resources, those two questions could
be answered by the Placement service as potential allocation candidates that
the filter would *only* be responsible for choosing between them in some
very specific cases (eg. PCI device NUMA affinity, CPU pinning and NUMA
anti-affinity).

Accordingly, we could model the host memory and the CPU topologies as a set of
resource providers arranged in a tree, and just directly allocate resources for
a specific instance from a resource provider subtree representing a NUMA node
and its resources.

That said, non resource-related features (like `choosing a specific CPU pin
within a NUMA node for a vCPU`_) would still be only done by the virt driver,
and are not covered by this spec.

Use Cases
---------

Consider the following NUMA topology for a "2-NUMA nodes, 4 cores" host with no
Hyper-Threading:

.. code::

    +--------------------------------------+
    |                  CN1                 |
    +-+---------------+--+---------------+-+
      |     NUMA1     |  |     NUMA2     |
      +-+----+-+----+-+  +-+----+-+----+-+
        |CPU1| |CPU2|      |CPU3| |CPU4|
        +----+ +----+      +----+ +----+

Here, CPU1 and CPU2 would share the same memory through a common memory
controller, while CPU3 and CPU4 would share their own memory.

Ideally, applications that require low-latency memory access from multiple
vCPUs on the same instance (for parallel computing reasons) would like to
ensure that those CPU resources are provided by the same NUMA node, or some
performance penalties would occur (if your application is CPU-bound or
I/O-bound of course). For the moment, if you're an operator, you can use flavor
extra specs to indicate a desired guest NUMA topology for your instance like:

.. code::

  $ openstack flavor set FLAVOR-NAME \
      --property hw:numa_nodes=FLAVOR-NODES \
      --property hw:numa_cpus.N=FLAVOR-CORES \
      --property hw:numa_mem.N=FLAVOR-MEMORY

See all the `NUMA possible extra specs`_ for a flavor.

.. note ::

  The example above is only needed when you want to not evenly divide your
  virtual CPUs and memory between NUMA nodes, of course.


Proposed change
===============

Given there are a lot of NUMA concerns, let's do an iterative approach about
the model we agree.

NUMA nodes being nested Resource Providers
------------------------------------------

Given virt drivers can amend a provider tree given by the compute node
ResourceTracker, then the libvirt driver could create child providers for each
of the 2 sockets representing separate NUMA node.

Since CPU resources are tied to a specific NUMA node, it makes sense to model
the corresponding resource classes as part of the child NUMA Resource
Providers. In order to facilitate querying NUMA resources, we propose to
decorate the NUMA child resource providers with a specific trait named
``HW_NUMA_ROOT`` that would be on each NUMA *node*. That would help to know
which hosts would be *NUMA-aware* and which others are not.

Memory is a bit tougher to represent. The granularity of a NUMA node having
an amount of attached memory is somehow a first approach but we're missing the
point that the smallest allocatable unit you can assign with Nova is
really a page size. Accordingly, we should rather model our NUMA subtree
with children Resource Providers that represent the smallest unit of memory
you can allocate, ie. a page size. Since a pagesize is not a *consumable*
amount but rather a *qualitative* information that helps us to allocate
``MEMORY_MB`` resources, we propose three traits :

- ``MEMORY_PAGE_SIZE_SMALL`` and ``MEMORY_PAGE_SIZE_LARGE`` would allow us to
  know whether the memory page size is default or optionally configured.

- ``CUSTOM_MEMORY_PAGE_SIZE_<X>`` where <X> is an integer would allow us to
  know the size of the page in KB. To make it clear, even if the trait is a
  custom one, it's important to have a naming convention for it so the
  scheduler could ask about page sizes without knowing all the traits.


.. code::

                                   +-------------------------------+
                                   |  <CN_NAME>                    |
                                   |  DISK_GB: 5                   |
                                   +-------------------------------+
                                   |  (no specific traits)         |
                                   +--+---------------------------++
                                      |                           |
                                      |                           |
               +-------------------------+                   +--------------------------+
               | <NUMA_NODE_O>           |                   | <NUMA_NODE_1>            |
               | VCPU: 8                 |                   | VCPU: 8                  |
               | PCPU: 16                |                   | PCPU: 8                  |
               +-------------------------+                   +--------------------------+
               | HW_NUMA_ROOT            |                   | HW_NUMA_ROOT             |
               +-------------------+-----+                   +--------------------------+
                 /                 |    \                                          /+\
                 +                 |     \_____________________________          .......
                 |                 |                                   \
   +-------------+-----------+   +-+--------------------------+   +-------------------------------+
   | <RP_UUID>               |   | <RP_UUID>                  |   | <RP_UUID>                     |
   | MEMORY_MB: 1024         |   | MEMORY_MB: 1024            |   |MEMORY_MB: 10240               |
   | step_size=1             |   | step_size=2                |   |step_size=1024                 |
   +-------------------------+   +----------------------------+   +-------------------------------+
   |MEMORY_PAGE_SIZE_SMALL   |   |MEMORY_PAGE_SIZE_LARGE      |   |MEMORY_PAGE_SIZE_LARGE         |
   |CUSTOM_MEMORY_PAGE_SIZE_4|   |CUSTOM_MEMORY_PAGE_SIZE_2048|   |CUSTOM_MEMORY_PAGE_SIZE_1048576|
   +-------------------------+   +----------------------------+   +-------------------------------+


.. note ::

    As we said above, we don't want to support children PCI devices for Ussuri
    at the moment. Other current children RPs for a root compute node, like
    ones for VGPU resources or bandwidth resources would still have their
    parent be the compute node.

NUMA RP
-------

Resource Provider names for NUMA nodes shall follow a convention of
``nodename_NUMA#`` where nodename would be the hypervisor hostname (given by
the virt driver) and where NUMA# would literally be a string made of 'NUMA'
postfixed by the NUMA cell ID which is provided by the virt driver.

Each NUMA node would be then a child Resource Provider, having two resource
classes :

* ``VCPU``: for telling how many virtual cores (not able to be pinned) the NUMA
  node has.
* ``PCPU``: for telling how many possible pinned cores the NUMA node has.

A specific trait should be decorating it as we explained : ``HW_NUMA_ROOT``.

Memory pagesize RP
------------------

Each `NUMA RP`_ should have child RPs for each possible memory page
size per host, and having a single resource class :

* ``MEMORY_MB``: for telling how much memory the NUMA node has in that specific
  page size.

This RP would be decorated by two traits :

 - either ``MEMORY_PAGE_SIZE_SMALL`` (default if not configured) or
   ``MEMORY_PAGE_SIZE_LARGE`` (if large pages are configured)

 - the size of the page size : CUSTOM_MEMORY_PAGE_SIZE_# (where # is the size
   in KB - default to 4 as the kernel defaults to 4KB page sizes)


Compute node RP
---------------

The root Resource Provider (ie. the compute node) would only provide resources
for classes that are not NUMA-related. Existing children RPs for vGPUs or
bandwidth-aware resources should still have this parent (until we discuss
about NUMA affinity for PCI devices).


Optionally configured NUMA resources
------------------------------------

Given there are NUMA workloads but also non-NUMA workloads, it's also important
for operators to just have compute nodes accepting the latter.
That said, having the compute node resources to be split between multiple
NUMA nodes could be a problem for those non-NUMA workloads if they want to keep
the existing behaviour.

For example, say an instance with 2 vCPUs and one host having 2 NUMA nodes but
each one only accepting one VCPU, then the Placement API wouldn't accept that
host (given each nested RP only accepts one VCPU). For that reason, we need to
have a configuration for saying which resources should be nested.
To reinforce the above, that means a host would be either NUMA or non-NUMA,
hence non-NUMA workloads being set on a specific NUMA node if host is set so.
The proposal we make here will be :

.. code::

  [compute]
  enable_numa_reporting_to_placement = <bool> (default None for Ussuri)


For below, we will tell hosts as "NUMA-aware" ones that have this option be
``True``. For hosts that have this option to ``False`` they are explicitely
asked to have a legacy behaviour and will be called "non-NUMA-aware".

Depending on the value of the option, Placement would accept or not a host
for the according request. The resulting matrix can be::

  +----------------------------------------+----------+-----------+----------+
  | ``enable_numa_reporting_to_placement`` | ``None`` | ``False`` | ``True`` |
  +========================================+==========+===========+==========+
  | NUMA-aware flavors                     | Yes      | No        | Yes      |
  +----------------------------------------+----------+-----------+----------+
  | NUMA-agnostic flavors                  | Yes      | Yes       | No       |
  +----------------------------------------+----------+-----------+----------+

where ``Yes`` means that there could be allocation candidates from this host,
while ``No`` means that no allocation candidates will be returned.

In order to distinghish compute nodes that have the ``False`` value instead of
``None``, we will decorate the former with a specific trait name
``HW_NON_NUMA``. Accordingly, we will query Placement by adding this forbidden
trait for *not* getting nodes that operators explicitly don't want them to
support NUMA-aware flavors.

.. note::
   By default, the value for that configuration option will be ``None`` for
   upgrade reasons. By the Ussuri timeframe, operators will have to decide
   which hosts they want to support NUMA-aware instances and which should be
   dedicated for 'non-NUMA-aware' instances. A `nova-status pre-upgrade check`
   command will be provided that will warn them to decide before upgrading to
   Victoria, if the default value is about to change as we could decide later
   in this cycle. Once we stop supporting ``None`` (in Victoria or later), the
   ``HW_NON_NUMA`` trait would no longer be needed so we could stop querying
   it.

.. note::
   Since we allow a transition period for helping the operators to decide, we
   will also make clear that this is a one-way change and that we won't
   provide a backwards support for turning a NUMA-aware host into a
   non-NUMA-aware host.

See the `Upgrade impact`_ section for further details.

.. note:: Since the discovery of a NUMA topology is made by virt drivers, it
          makes the population of those nested Resource Providers to necessarly
          be done by each virt driver. Consequently, while the above
          configuration option is said to be generic, the use of this option
          for populating the Resource Providers tree will only be done by
          the virt drivers. Of course, a shared module could be imagined for
          the sake of consistency between drivers, but this is an
          implementation detail.


The very simple case: I don't care about a NUMA-aware instance
--------------------------------------------------------------

For flavors just asking for, say, vCPUs and memory without asking them to be
NUMA-aware, then we will make a single Placement call asking to *not* land
them on a NUMA-aware host::

    resources=VCPU:<X>,MEMORY_MB=<Y>
    &required=!HW_NUMA_ROOT

In this case, even if NUMA-aware hosts have enough resources for this query,
the Placement API won't provide them but only non-NUMA-aware ones (given the
forbidden ``HW_NUMA_ROOT`` trait).
We're giving the possibility to the operator to shard their clouds between
NUMA-aware hosts and non-NUMA-aware hosts but that's not really changing the
current behaviour as of now where operators create aggregates to make sure
non-NUMA-aware instances can't land on NUMA-aware hosts.

See the `Upgrade impact` session for rolling upgrade situations where clouds
are partially upgraded to Ussuri and where only a very few nodes are reshaped.


Asking for NUMA-aware vCPUs
---------------------------

As NUMA-aware hosts have a specific topology with memory being in a grand-child
RP, we basically need to ensure we can translate the existing expressiveness in
the flavor extra specs into a Placement allocation candidates query that asks
for parenting between the NUMA RP containing the ``VCPU`` resources and the
memory pagesize RP containing the ``MEMORY_MB`` resources.

Accordingly, here are some examples:

* for a flavor of 8 VCPUs, 8GB of RAM and ``hw:numa_nodes=2``::

    resources_MEM1=MEMORY_MB:4096
    &required_MEM1=MEMORY_PAGE_SIZE_SMALL
    &resources_PROC1=VCPU:4
    &required_NUMA1=HW_NUMA_ROOT
    &same_subtree=_MEM1,_PROC1,_NUMA1
    &resources_MEM2=MEMORY_MB:4096
    &required_MEM2=MEMORY_PAGE_SIZE_SMALL
    &resources_PROC2=VCPU:4
    &required_NUMA2=HW_NUMA_ROOT
    &same_subtree=_MEM2,_PROC2,_NUMA2
    &group_policy=none


.. note::
   We use ``none`` as a value for ``group_policy`` which means that in this
   example, allocation candidates can all be from ``PROC1`` group meaning
   that we defeat the purpose of having the resources separated into different
   NUMA nodes (which is the purpose of ``hw:numa_nodes=2``). This is OK
   as we will also modify the ``NUMATopologyFilter`` to only accept
   allocation candidates for a host that are in different NUMA nodes.
   It will probably be implemented in the ``nova.virt.hardware`` module but
   that's an implementation detail.

* for a flavor of 8 VCPUs, 8GB of RAM and ``hw:numa_nodes=1``::

    resources_MEM1=MEMORY_MB:8192
    &required_MEM1=MEMORY_PAGE_SIZE_SMALL
    &resources_PROC1=VCPU:8
    &required_NUMA1=HW_NUMA_ROOT
    &same_subtree=_MEM1,_PROC1,_NUMA1

* for a flavor of 8 VCPUs, 8GB of RAM and
  ``hw:numa_nodes=2&hw:numa_cpus.0=0,1&hw:numa_cpus.1=2,3,4,5,6,7``::

    resources_MEM1=MEMORY_MB:4096
    &required_MEM1=MEMORY_PAGE_SIZE_SMALL
    &resources_PROC1=VCPU:2
    &required_NUMA1=HW_NUMA_ROOT
    &same_subtree=_MEM1,_PROC1,_NUMA1
    &resources_MEM2=MEMORY_MB:4096
    &required_MEM2=MEMORY_PAGE_SIZE_SMALL
    &resources_PROC2=VCPU:6
    &required_NUMA2=HW_NUMA_ROOT
    &same_subtree=_MEM2,_PROC2,_NUMA2
    &group_policy=none

* for a flavor of 8 VCPUs, 8GB of RAM and
  ``hw:numa_nodes=2&hw:numa_cpus.0=0,1&hw:numa_mem.0=1024
  &hw:numa_cpus.1=2,3,4,5,6,7&hw:numa_mem.1=7168``::

    resources_MEM1=MEMORY_MB:1024
    &required_MEM1=MEMORY_PAGE_SIZE_SMALL
    &resources_PROC1=VCPU:2
    &required_NUMA1=HW_NUMA_ROOT
    &same_subtree=_MEM1,_PROC1,_NUMA1
    &resources_MEM2=MEMORY_MB:7168
    &required_MEM2=MEMORY_PAGE_SIZE_SMALL
    &resources_PROC2=VCPU:6
    &required_NUMA2=HW_NUMA_ROOT
    &same_subtree=_MEM2,_PROC2,_NUMA2
    &group_policy=none

As you can understand, the ``VCPU`` and ``MEMORY_MB`` values will be a result
of the division of respectively the flavored vCPUs and the flavored memory by
the value of ``hw:numa_nodes`` (which is actually already calculated and
provided as NUMATopology object information in the RequestSpec object).

.. note::
   The translation mechanism from a flavor-based request into Placement query
   will be handled by the scheduler service.

.. note::
   Since memory is provided as grand-child, we need to always ask for a
   ``MEMORY_PAGE_SIZE_SMALL`` which is the default.


Asking for specific memory page sizes
-------------------------------------


Operators defining a flavor of 2 vCPUs, 4GB of RAM and
``hw:mem_page_size=2MB,hw:numa_nodes=2`` will see that the Placement query will
become::

    resources_PROC1=VCPU:1
    &resources_MEM1=MEMORY_MB:2048
    &required_MEM1=CUSTOM_MEMORY_PAGE_SIZE_2048
    &required_NUMA1=HW_NUMA_ROOT
    &same_subtree=_PROC1,_MEM1,_NUMA1
    &resources_PROC2=VCPU:1
    &resources_MEM2=MEMORY_MB:2048
    &required_MEM2=CUSTOM_MEMORY_PAGE_SIZE_2048
    &required_NUMA2=HW_NUMA_ROOT
    &same_subtree=_PROC2,_MEM2,_NUMA2
    &group_policy=none

If you only want large page size support without really specifying which size
(eg. by specifying ``hw:mem_page_size=large`` instead of, say, ``2MB``), then
the above same request for large pages would translate into::

    resources_PROC1=VCPU:1
    &resources_MEM1=MEMORY_MB:2048
    &required_MEM1=MEMORY_PAGE_SIZE_LARGE
    &required_NUMA1=HW_NUMA_ROOT
    &same_subtree=_PROC1,_MEM1,_NUMA1
    &resources_PROC2=VCPU:1
    &resources_MEM2=MEMORY_MB:2048
    &required_MEM2=MEMORY_PAGE_SIZE_LARGE
    &required_NUMA2=HW_NUMA_ROOT
    &same_subtree=_PROC2,_MEM2,_NUMA2
    &group_policy=none

Asking the same with ``hw:mem_page_size=small`` would translate into::

    resources_PROC1=VCPU:1
    &resources_MEM1=MEMORY_MB:2048
    &required_MEM1=MEMORY_PAGE_SIZE_SMALL
    &required_NUMA1=HW_NUMA_ROOT
    &same_subtree=_PROC1,_MEM1,_NUMA1
    &resources_PROC2=VCPU:1
    &resources_MEM2=MEMORY_MB:2048
    &required_MEM2=MEMORY_PAGE_SIZE_SMALL
    &required_NUMA2=HW_NUMA_ROOT
    &same_subtree=_PROC2,_MEM2,_NUMA2
    &group_policy=none

And eventually, asking with ``hw:mem_page_size=any`` would mean::

    resources_PROC1=VCPU:1
    &resources_MEM1=MEMORY_MB:2048
    &required_NUMA1=HW_NUMA_ROOT
    &same_subtree=_PROC1,_MEM1,_NUMA1
    &resources_PROC2=VCPU:1
    &resources_MEM2=MEMORY_MB:2048
    &required_NUMA2=HW_NUMA_ROOT
    &same_subtree=_PROC2,_MEM2,_NUMA2
    &group_policy=none


.. note:: As we said for vCPUs, given we query with ``group_policy=none``,
   allocation candidates would be within the same NUMA node but that's fine
   since we also said that the scheduler filter would then no agree with
   them if there is a ``hw:numa_nodes=X`` there.

The fallback case for NUMA-aware flavors
----------------------------------------

In the `Optionally configured NUMA resources`_ section, we said that we would
want to accept NUMA-aware flavors to land on hosts that have the
``enable_numa_reporting_to_placement`` option set to ``None``. Since we can't
yet build a ``OR`` query for allocation candidates, we propose to make another
call to Placement.
In this specific call (we name it a fallback call), we want to get all
non-reshaped nodes that are *not* explicitly said to not support NUMA.
In this case, the request is fairly trivial since we decorated them with the
``HW_NON_NUMA`` trait::

  resources=VCPU:<X>,MEMORY_MB=<Y>
  &required=!HW_NON_NUMA,!HW_NUMA_ROOT

Then we would get all compute nodes that have the ``None`` value (
including nodes that are still running the Train release in a rolling upgrade
fashion).

Of course, we would get nodes that could potentially *not* accept the
NUMA-aware flavor but we rely on the ``NUMATopologyFilter`` for not selecting
them, exactly like what we do in Train.

There is some open question about whether we should do the fallback call only
if the NUMA-specific call is not getting candidates or if we should generate
the two calls either way and merge the results.
The former is better for performance reasons since we avoid a potentially
unnecessary call but would generate some potential spread/pack affinity issues.
Here we all agree on the fact we can leave the question unresolved for now and
defer the resolution to the implementation phase.

Alternatives
------------

Modeling of NUMA resources could be done by using specific NUMA resource
classes, like ``NUMA_VCPU`` or ``NUMA_MEMORY_MB`` that would only be set for
children NUMA resource providers, and where ``VCPU`` and ``MEMORY_MB`` resource
classes would only be set on the root Resource Provider (here the compute
node).

If the Placement allocations candidates API was also able to provide a way to
say 'you can split the resources between resource providers', we wouldn't need
to carry a specific configuration option for a long time. All hosts would then
be reshaped to be NUMA-aware but then non-NUMA-aware instances could
potentially land on those hosts. That wouldn't change the fact that for
optimal capacity, operators need to shard their clouds between NUMA workloads
and non-NUMA ones, but from a Placement perspective, all hosts would be equal.
This alternative proposal has largely already been discussed in a
spec but the outcome consensus was that it was very
difficult to implement and potentially not worth the difficulty.

Data model impact
-----------------
None

REST API impact
---------------

None

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------

None, flavors won't need to be modified since we will provide a translation
mechanism. That said, we will explicitly explain in the documentation that
we won't support any placement-like extra specs in flavors.

Performance Impact
------------------

Only when changing the configuration option to ``True``, a reshape is done.

Other deployer impact
---------------------

Operators would want to migrate some instances from hosts to anothers before
explicitely enabling or disabling NUMA awareness on their nodes since they will
have to consider the capacity usage accordingly as they will have to shard
their cloud. This being said, this would only be necessary for clouds that
weren't yet already dividing NUMA-aware and non-NUMA-aware workloads between
hosts thru aggregates.

Developer impact
----------------

None, except virt driver maintainers.

Upgrade impact
--------------

As described above, in order to prevent a flavor update during upgrade, we will
provide a translation mechanism that will take the existing
flavor extra spec properties and transform them into Placement numbered groups
query.

Since there will be a configuration option for telling that a host would become
NUMA-aware, the corresponding allocations accordingly have to change hence the
virt drivers be responsible for providing a reshape mechanism that will
eventually call the `Placement API /reshaper endpoint`_ when starting the
compute service. This reshape implementation will absolutely need to consider
the Fast Forward Upgrade (FFU) strategy where all controlplane is down and
should possibly document any extra step required for FFU with an eventual
removal in a couple of releases once all deployers no longer need this support.

Last but not the least, we will provide a transition period (at least during
the Ussuri timeframe) where operators can decide which hosts to dedicate to
NUMA-aware workloads. A specific ``nova-status pre-upgrade check`` command
will warn them to do so before upgrading to Victoria.


Implementation
==============

Assignee(s)
-----------

* bauzas
* sean-k-mooney

Feature Liaison
---------------
bauzas

Work Items
----------

* libvirt driver passing NUMA topology through ``update_provider_tree()`` API
* Hyper-V driver passing NUMA topology through ``update_provider_tree()`` API
* Possible work on the NUMATopologyFilter to look at the candidates
* Scheduler translating flavor extra specs for NUMA properties into Placement
  queries
* ``nova-status pre-upgrade check`` command


Dependencies
============

None.


Testing
=======

Functional tests and unittests.

Documentation Impact
====================

None.

References
==========

* _`Nested Resource Providers`: https://specs.openstack.org/openstack/nova-specs/specs/queens/approved/nested-resource-providers.html
* _`choosing a specific CPU pin within a NUMA node for a vCPU`: https://docs.openstack.org/nova/latest/admin/cpu-topologies.html#customizing-instance-cpu-pinning-policies
* _`NUMA possible extra specs`: https://docs.openstack.org/nova/latest/admin/flavors.html#extra-specs-numa-topology
* _`Huge pages`: https://docs.openstack.org/nova/latest/admin/huge-pages.html
* _`Placement API /reshaper endpoint`: https://developer.openstack.org/api-ref/placement/?expanded=id84-detail#reshaper
* _`Placement can_split`: https://review.opendev.org/#/c/658510/
* _`physical CPU resources`: https://specs.openstack.org/openstack/nova-specs/specs/train/approved/cpu-resources.html
