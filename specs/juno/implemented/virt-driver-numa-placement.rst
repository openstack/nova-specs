..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
Virt driver guest NUMA node placement & topology
================================================

https://blueprints.launchpad.net/nova/+spec/virt-driver-numa-placement

This feature aims to enhance the libvirt driver to be able to do intelligent
NUMA node placement for guests. This will increase the effective utilization
of compute resources and decrease latency by avoiding cross-node memory
accesses by guests.

Problem description
===================

The vast majority of hardware used for virtualization compute nodes will
exhibit NUMA characteristics. When running workloads on NUMA hosts it is
important that the CPUs executing the processes are on the same node as the
memory used. This ensures that all memory accesses are local to the NUMA node
and thus not consumed the very limited cross-node memory bandwidth, which adds
latency to memory accesses. PCI devices are directly associated with specific
NUMA nodes for the purposes of DMA, so when using PCI device assignment it is
also desirable that the guest be placed on the same NUMA node as any PCI device
that is assigned to it.

The libvirt driver does not currently attempt any NUMA placement, the guests
are free to float across any host pCPUs and their RAM is allocated from any
NUMA node. This is very wasteful of compute resources and increases memory
access latency which is harmful for NFV use cases.

If the RAM/vCPUs associated with a flavor are larger than any single NUMA
node, it is important to expose NUMA topology to the guest so that the OS in
the guest can intelligently schedule workloads it runs. For this to work the
guest NUMA nodes must be directly associated with host NUMA nodes.

Some guest workloads have very demanding requirements for memory access
latency and/or bandwidth, which exceed that which is available from a
single NUMA node. For such workloads, it will be beneficial to spread
the guest across multiple host NUMA nodes, even if the guest RAM/vCPUs
could theoretically fit in a single NUMA node.

Forward planning to maximise the choice of target hosts for use with live
migration may also cause an administrator to prefer splitting a guest
across multiple nodes, even if it could potentially fit in a single node
on some hosts.

For these two reasons it is desirable to be able to explicitly indicate
how many NUMA nodes to setup in a guest, and to specify how much RAM or
how many vCPUs to place in each node.

Proposed change
===============

The libvirt driver will be enhanced so that it looks at the resources available
in each NUMA node and decides which is best able to run the guest. When
launching the guest, it will tell libvirt to confine the guest to the chosen
NUMA node.

The compute driver host stats data will be extended to include information
about the NUMA topology of the host and the availability of resources in the
nodes.

The scheduler will be enhanced such that it can consider the availability of
NUMA resources when choosing the host to schedule on. The algorithm that the
scheduler uses to decide if the host can run will need to be closely matched,
if not identical to, the algorithm used by the libvirt driver itself. This
will involve the creation of a new scheduler filter to match the flavor/image
config specification against the NUMA resource availability reported by the
compute hosts.

The flavor extra specs will support the specification of guest NUMA topology.
This is important when the RAM / vCPU count associated with a flavor is larger
than any single NUMA node in compute hosts, by making it possible to have guest
instances that span NUMA nodes. The compute driver will ensure that guest NUMA
nodes are directly mapped to host NUMA nodes. It is expected that the default
setup would be to not list any NUMA properties and just let the compute host
and scheduler apply a sensible default placement logic. These properties would
only need to be set in the sub-set of scenarios which require more precise
control over the NUMA topology / fit characteristics.

* hw:numa_nodes=NN - numa of NUMA nodes to expose to the guest.
* hw:numa_mempolicy=preferred|strict - memory allocation policy
* hw:numa_cpus.0=<cpu-list> - mapping of vCPUS N-M to NUMA node 0
* hw:numa_cpus.1=<cpu-list> - mapping of vCPUS N-M to NUMA node 1
* hw:numa_mem.0=<ram-size> - mapping N MB of RAM to NUMA node 0
* hw:numa_mem.1=<ram-size> - mapping N MB of RAM to NUMA node 1

The most common case will be that the admin only sets 'hw:numa_nodes' and then
the flavor vCPUs and RAM will be divided equally across the NUMA nodes.

The 'hw:numa_mempolicy' option allows specification of whether it is mandatory
for the instance's RAM allocations to come from the NUMA nodes to which it is
bound, or whether the kernel is free to fallback to using an alternative node.
If 'hw:numa_nodes' is specified, then 'hw:numa_mempolicy' is assumed to default
to 'strict'. It is useful to change it to 'preferred' when the 'hw:numa_nodes'
parameter is being set to '1' to force disable use of NUMA by image property
overrides.

It should only be required to use the 'hw:numa_cpu.N' and 'hw:numa_mem.N'
settings if the guest NUMA nodes should have asymetrical allocation of CPUs
and RAM. This is important for some NFV workloads, but in general these will
be rarely used tunables. If the 'hw:numa_cpu' or 'hw:numa_mem' settings are
provided and their values do not sum to the total vcpu count / memory size,
this is considered to be a configuration error. An exception will be raised
by the compute driver when attempting to boot the instance. As an enhancement
it might be possible to validate some of the data at the API level to allow
for earlier error reporting to the user. Such checking is not a functional
prerequisite for this work though so such work can be done out-of-band to
the main development effort.

When scheduling, if only the hw:numa_nodes=NNN property is set the scheduler
will synthesize hw:numa_cpus.NN and hw:numa_mem.NN properties such that the
flavor allocation is equally spread across the desired number of NUMA nodes.
It will then look consider the available NUMA resources on hosts to find one
that exactly matches the requirements of the guest. So, given an example
config:

* vcpus=8
* mem=4
* hw:numa_nodes=2 - numa of NUMA nodes to expose to the guest.
* hw:numa_cpus.0=0,1,2,3,4,5
* hw:numa_cpus.1=6,7
* hw:numa_mem.0=3072
* hw:numa_mem.1=1024

The scheduler will look for a host with 2 NUMA nodes with the ability to run
6 CPUs + 3 GB of RAM on one node, and 2 CPUS + 1 GB of RAM on another node.
If a host has a single NUMA node with capability to run 8 CPUs and 4 GB of
RAM it will not be considered a valid match. The same logic will be applied
in the scheduler regardless of the hw:numa_mempolicy option setting.

All of the properties described against the flavor could also be set against
the image, with the leading ':' replaced by '_', as is normal for image
property naming conventions:

* hw_numa_nodes=NN - numa of NUMA nodes to expose to the guest.
* hw_numa_mempolicy=strict|prefered - memory allocation policy
* hw_numa_cpus.0=<cpu-list> - mapping of vCPUS N-M to NUMA node 0
* hw_numa_cpus.1=<cpu-list> - mapping of vCPUS N-M to NUMA node 1
* hw_numa_mem.0=<ram-size> - mapping N MB of RAM to NUMA node 0
* hw_numa_mem.1=<ram-size> - mapping N MB of RAM to NUMA node 1

This is useful if the application in the image requires very specific NUMA
topology characteristics, which is expected to be used frequently with NFV
images. The properties can only be set against the image, however, if they
are not already set against the flavor. So for example, if the flavor sets
'hw:numa_nodes=2' but does not set any 'hw:numa_cpus' / 'hw:numa_mem' values
then the image can optionally set those. If the flavor has, however, set a
specific property the image cannot override that. This allows the flavor
admin to strictly lock down what is permitted if desired. They can force a
non-NUMA topology by setting hw:numa_nodes=1 against the flavor.

Alternatives
------------

Libvirt supports integration with a daemon called numad. This daemon can be
given a RAM size + vCPU count and tells libvirt what NUMA node to place a
guest on. It is also capable of shifting running guests between NUMA nodes to
rebalance utilization. This is insufficient for Nova since it needs to have
intelligence in the scheduler to pick hosts. The compute drivers then needs to
be able to use the same logic when actually launching the guests. The numad
system is not portable to other compute hypervisors. It does not deal with the
problem of placing guests which span across NUMA nodes. Finally, it does not
address the needs for NFV workloads which require guaranteed NUMA topology
and placement policies, not merely dynamic best effort.

Another alternative is to just do nothing, as we do today, and rely on the
Linux kernel scheduler being enhanced to automatically place guests on
appropriate NUMA nodes and rebalance them on demand. This shares most of the
problems seen with using numad.

Data model impact
-----------------

No impact.

The reporting of NUMA topology will be integrated in the existing data
structure used for host state reporting. This already supports arbitrary
fields so no data model changes are anticipated for this part. This would
appear as structured data

::

  hw_numa = {
     nodes = [
         {
            id = 0
            cpus = 0, 2, 4, 6
            mem = {
               total = 10737418240
               free = 3221225472
            },
            distances = [ 10, 20],
         },
         {
            id = 1
            cpus = 1, 3, 5, 7
            mem = {
               total = 10737418240
               free = 5368709120
            },
            distances = [ 20, 10],
         }
     ],
  }


REST API impact
---------------

No impact.

The API for host state reporting already supports arbitrary data fields, so
no change is anticipated from that POV. No new API calls will be required.

Security impact
---------------

No impact.

There are no new APIs involved which would imply a new security risk.

Notifications impact
--------------------

No impact.

There is no need for any use fo the notification system.

Other end user impact
---------------------

Depending on the flavor chosen, the guest OS may see NUMA nodes backing its
RAM allocation.

There is no end user interaction in setting up NUMA policies of usage.

The cloud administrator will gain the ability to set policies on flavors.

Performance Impact
------------------

The new scheduler features will imply increased performance overhead when
determining whether a host is able to fit the memory and vCPU needs of the
flavor. ie the current logic which just checks the vCPU count and RAM
requirement against the host free memory will need to take account of the
availability of resources in specific NUMA nodes.

Other deployer impact
---------------------

If the deployment has flavors whose RAM + vCPU allocations are larger than
the size of the NUMA nodes in the compute hosts, the cloud administrator
should strongly consider defining guest NUMA nodes in the flavor. This will
enable the compute hosts to have better NUMA utilization and improve perf of
the guest OS.

Developer impact
----------------

The new flavor attributes could be used by any full machine virtualization
hypervisor, however, it is not mandatory that they do so.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  berrange

Other contributors:
  ndipanov

Work Items
----------

* Enhance libvirt driver to report NUMA node resources & availability
* Enhance libvirt driver to support setup of guest NUMA nodes.
* Enhance libvirt driver to look at NUMA node availability when launching
  guest instances and pin all guests to best NUMA node
* Add support to schedular for picking hosts based on the NUMA availability
  instead of simply considering the total RAM/vCPU availability.

Dependencies
============

* The driver vCPU topology feature is a pre-requisite

    https://blueprints.launchpad.net/nova/+spec/virt-driver-vcpu-topology

* Supporting guest NUMA nodes will require completion of work in QEMU and
  libvirt, to enable guest NUMA nodes to be pinned to specific host NUMA
  nodes. In absence of libvirt/QEMU support, guest NUMA nodes can still be
  used but it would not have any performance benefit, and may even hurt
  performance.

    https://www.redhat.com/archives/libvir-list/2014-June/msg00201.html

Testing
=======

There are various discrete parts of the work that can be tested in isolation
of each other, fairly effectively using unit tests.

The main area where unit tests might not be sufficient is the scheduler
integration, where performance/scalability would be a concern. Testing the
scalability of the scheduler in tempest though is not practical, since the
issues would only become apparent with many compute hosts and many guests.
ie a scale beyond that which tempest sets up.

Documentation Impact
====================

The cloud administrator docs need to describe the new flavor parameters
and make recommendations on how to effectively use them.

The end user needs to be made aware of the fact that some flavors will cause
the guest OS to see NUMA topology.

References
==========

Current "big picture" research and design for the topic of CPU and memory
resource utilization and placement. vCPU topology is a subset of this
work

* https://wiki.openstack.org/wiki/VirtDriverGuestCPUMemoryPlacement

OpenStack NFV team:

* https://wiki.openstack.org/wiki/Teams/NFV
