..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Virt driver pinning guest vCPUs to host pCPUs
=============================================

https://blueprints.launchpad.net/nova/+spec/virt-driver-cpu-pinning

This feature aims to improve the libvirt driver so that it is able to strictly
pin guest vCPUS to host pCPUs. This provides the concept of "dedicated CPU"
guest instances.

Problem description
===================

If a host is permitting overcommit of CPUs, there can be prolonged time
periods where a guest vCPU is not scheduled by the host, if another guest is
competing for the CPU time. This means that workloads executing in a guest can
have unpredictable latency, which may be unacceptable for the type of
application being run.


Use Cases
---------

Depending on the workload being executed the end user or cloud admin may
wish to have control over how the guest used hyperthreads. To maximise cache
efficiency, the guest may wish to be pinned to thread siblings. Conversely
the guest may wish to avoid thread siblings (ie only pin to 1 sibling)
or even avoid hosts with threads entirely. This level of control is of
particular importance to Network Function Virtualization (NFV) deployments
which care about maximising cache efficiency of vCPUs.

Project Priority
----------------

None

Proposed change
===============

The flavor extra specs will be enhanced to support two new parameters

* hw:cpu_policy=shared|dedicated
* hw:cpu_threads_policy=avoid|separate|isolate|prefer

If the policy is set to 'shared' no change will be made compared to the current
default guest CPU placement policy. The guest vCPUs will be allowed to freely
float across host pCPUs, albeit potentially constrained by NUMA policy. If the
policy is set to 'dedicated' then the guest vCPUs will be strictly pinned to a
set of host pCPUs. In the absence of an explicit vCPU topology request, the
virt drivers typically expose all vCPUs as sockets with 1 core and 1 thread.
When strict CPU pinning is in effect the guest CPU topology will be setup to
match the topology of the CPUs to which it is pinned. ie if a 2 vCPU guest is
pinned to a single host core with 2 threads, then the guest will get a topology
of 1 socket, 1 core, 2 threads.

The threads policy will control how the scheduler / virt driver places guests
with resepct to CPU threads. It will only apply if the scheduler policy is
'dedicated'

 - avoid: the scheduler will not place the guest on a host which has
   hyperthreads.
 - separate: if the host has threads, each vCPU will be placed on a
   different core. ie no two vCPUs will be placed on thread siblings
 - isolate: if the host has threads, each vCPU will be placed on a
   different core and no vCPUs from other guests will be able to be
   placed on the same core. ie one thread sibling is guaranteed to
   always be unused,
 - prefer: if the host has threads, vCPU will be placed on the same
   core, so they are thread siblings.

The image metadata properties will also allow specification of the
threads policy

* hw_cpu_threads_policy=avoid|separate|isolate|prefer

This will only be honoured if the flavor does not already have a threads
policy set. This ensures the cloud administrator can have absolute control
over threads policy if desired.

The scheduler will have to be enhanced so that it considers the usage of CPUs
by existing guests. Use of a dedicated CPU policy will have to be accompanied
by the setup of aggregates to split the hosts into two groups, one allowing
overcommit of shared pCPUs and the other only allowing dedicated CPU guests.
ie we do not want a situation with dedicated CPU and shared CPU guests on the
same host. It is likely that the administrator will already need to setup host
aggregates for the purpose of using huge pages for guest RAM. The same grouping
will be usable for both dedicated RAM (via huge pages) and dedicated CPUs (via
pinning).

The compute host already has a notion of CPU sockets which are reserved for
execution of base operating system services. This facility will be preserved
unchanged. ie dedicated CPU guests will only be placed on CPUs which are not
marked as reserved for the base OS.

Alternatives
------------

There is no alternative way to ensure that a guest has predictable execution
latency free of cache effects from other guests working on the host, that does
not involve CPU pinning.

The proposed solution is to use host aggregates for grouping compute hosts into
those for dedicated vs overcommit CPU policy. An alternative would be to allow
compute hosts to have both dedicated and overcommit guests, splitting them onto
separate sockets. ie if there were for sockets, two sockets could be used for
dedicated CPU guests while two sockets could be used for overcommit guests,
with usage determined on a first-come, first-served basis. A problem with this
approach is that there is not strict workload isolation even if separate
sockets are used. Cached effects can be observed, and they will also contend
for memory access, so the overcommit guests can negatively impact performance
of the dedicated CPU guests even if on separate sockets. So while this would
be simpler from an administrative POV, it would not give the same performance
guarantees that are important for NFV use cases. It would none the less be
possible to enhance the design in the future, so that overcommit & dedicated
CPU guests could co-exist on the same host for those use cases where admin
simplicity is more important than perfect performance isolation. It is believed
that it is better to start off with the simpler to implement design based on
host aggregates for the first iteration of this feature.

Data model impact
-----------------

The 'compute_node' table will gain a new field to record information about
what host CPUs are available and what are in use by guest instances with
dedicated CPU resource assigned. Similar to the 'numa_topology' field this
will be a structured data field containing something like

::

  {'cells': [
            {
                'cpuset': '0,1,2,3',
                'sib': ['0,1', '2,3'],
                'pin': '0,2',
                'id': 0
            },
            {
                'cpuset': '4,5,6,7',
                'sib': ['4,5', '6,7'],
                'pin': '4',
                'id': 1
            }
  ]}

The 'instance_extra' table will gain a new field to record information
about what host CPUs each guest CPU is being pinned to, which will also
contain structured data similar to that used in the 'numa_topology' field
of the same table.

::

 {'cells': [
            {
                'id': 0,
                'pin': {0: 0, 1: 3},
                'topo': {'sock': 1, 'core': 1, 'th': 2}
            },
            {
                'id': 1,
                'pin': {2: 1, 3: 2},
                'topo': {'sock': 1, 'core': 1, 'th': 2}
            }
 ]}


REST API impact
---------------

No impact.

The existing APIs already support arbitrary data in the flavor extra specs.

Security impact
---------------

No impact.

Notifications impact
--------------------

No impact.

The notifications system is not used by this change.

Other end user impact
---------------------

There are no changes that directly impact the end user, other than the fact
that their guest should have more predictable CPU execution latency.

Performance Impact
------------------

The scheduler will incur small further overhead if a threads policy is set
on the image or flavor. This overhead will be negligible compared to that
implied by the enhancements to support NUMA policy and huge pages. It is
anticipated that dedicated CPU guests will typically be used in conjunction
with huge pages.

Other deployer impact
---------------------

The cloud administrator will gain the ability to define flavors which offer
dedicated CPU resources. The administrator will have to place hosts into groups
using aggregates such that the scheduler can separate placement of guests with
dedicated vs shared CPUs. Although not required by this design, it is expected
that the administrator will commonly use the same host aggregates to group
hosts for both CPU pinning and large page usage, since these concepts are
complementary and expected to be used together. This will minimise the
administrative burden of configuring host aggregates.

Developer impact
----------------

It is expected that most hypervisors will have the ability to setup dedicated
pCPUs for guests vs shared pCPUs. The flavor parameter is simple enough that
any Nova driver would be able to support it.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  ndipanov

Other contributors:
  berrange
  vladik

Work Items
----------

* Enhance libvirt to support setup of strict CPU pinning for guests when the
  appropriate policy is set in the flavor

* Enhance the scheduler to take account of threads policy when choosing
  which host to place the guest on.

Dependencies
============

* Virt driver guest NUMA node placement & topology

   https://blueprints.launchpad.net/nova/+spec/virt-driver-numa-placement

Testing
=======

It is not practical to test this feature using the gate and tempest at this
time, since effective testing will require that the guests running the test
be provided with multiple NUMA nodes, each in turn with multiple CPUs.

The Nova docs/source/devref documentation will be updated to include a
detailed set of instructions for manually testing the feature. This will
include testing of the previously developed NUMA and huge pages features
too. This doc will serve as the basis for later writing further automated
tests, as well as a useful basis for writing end user documentation on
the feature.

Documentation Impact
====================

The new flavor parameter available to the cloud administrator needs to be
documented along with recommendations about effective usage. The docs will
also need to mention the compute host deployment pre-requisites such as the
need to setup aggregates. The testing guide mentioned in the previous
section will provide useful material for updating the docs with.

References
==========

Current "big picture" research and design for the topic of CPU and memory
resource utilization and placement. vCPU topology is a subset of this
work

* https://wiki.openstack.org/wiki/VirtDriverGuestCPUMemoryPlacement

Previously approved for Juno but implementation not completed

* https://review.openstack.org/93652
