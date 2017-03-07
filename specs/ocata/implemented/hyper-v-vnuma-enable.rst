..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Hyper-V vNUMA enable
====================

https://blueprints.launchpad.net/nova/+spec/hyper-v-vnuma-enable

Windows Hyper-V / Server 2012 introduces support for vNUMA topology into
Hyper-V virtual machines. This feature improves the performance for VMs
configured with large amounts of memory.

Problem description
===================

Currently, there is no support for Hyper-V instances with vNUMA enabled. This
blueprint addresses this issue.

Use Cases
----------

NUMA can improve the performance of workloads running on virtual machines that
are configured with large amounts of memory. This feature is useful for
high-performance NUMA-aware applications, such as database or web servers.

Hyper-V presents a virtual NUMA topology to VMs. By default, this virtual NUMA
topology is optimized to match the NUMA topology of the underlying host.
Exposing a virtual NUMA topology into a virtual machine allows the guest OS and
any NUMA-aware applications running within it to take advantage of the NUMA
performance optimizations, just as they would when running on a physical
computer. [1]

Hyper-V related restrictions:

* Hyper-V cannot create instances with asymmetric NUMA topology.
* Hyper-V cannot guarantee CPU pinning.


Proposed change
===============

If VM vNUMA is enabled, Hyper-V will attempt to allocate all of the memory for
that VM from a single physical NUMA node. If the memory requirement cannot be
satisfied by a single node, Hyper-V allocates memory from another physical NUMA
node. This is called NUMA spanning.

If vNUMA is enabled, the VM can have assigned up to 64 vCPUs and 1 TB memory.
If vNUMA is enabled, the VM cannot have Dynamic Memory enabled.

The Host NUMA topology can be queried, yielding an object for each of the
host's NUMA nodes. If the result is only a single object, the host is not
NUMA based. Resulting NUMA node object looks like this:

    NodeId                 : 0
    ProcessorsAvailability : {94, 99, 100, 100}
    MemoryAvailable        : 3196
    MemoryTotal            : 4093
    ComputerName           : ServerName_01

The Host NUMA topology will have to be reported by HyperVDriver when the
method ``get_available_resource`` is called. The returned dictionary will
contain the ``numa_topology`` field and it will contain an array with
NumaTopology objects, converted to json.

The scheduler has already been enhanced to consider the availability of NUMA
resources when choosing the host to schedule the instance on. [2]

Virtual NUMA topology can be configured for each individual VM. The maximum
amount of memory and the maximum number of virtual processors in each virtual
NUMA node can be configured.

Instances with vNUMA enabled are requested via flavor extra specs [2]:

* hw:numa_nodes=NN - number of NUMA nodes to expose to the guest.

HyperVDriver must check if the instances require CPU pinning or asymmetric
NUMA topology. As they are not supported, it should raise an Exception.

Equivalent image properties can be defined, with an '_' instead of ':'.
(example: hw_numa_nodes=NN). Flavor extra specs will override the equivalent
image properties.

More details about the flavor extra specs and image properties can be found
in the References section [2]. The implementation will be done in as similar
fashion as libvirt.

Alternatives
------------

None, there is no alternative to enable vNUMA with the current HyperVDriver.

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

None

Performance Impact
------------------

This capability can help improve the performance of workloads running on
virtual machines that are configured with large amounts of memory.

Other deployer impact
---------------------

If the Host NUMA spanning is enabled, virtual machines can use whatever memory
is available on the method, regardless of its distribution across the physical
NUMA nodes. This can cause varying VM performances between VM restarts. NUMA
spanning is enabled by default.

Checking the available host NUMA nodes can easily be done by running the
following Powershell command:

  Get-VMHostNumaNode

If only one NUMA node is revealed, it means that the system is not NUMA-based.
Disabling NUMA spanning will not bring any advantage.

There are advantages and disadvantages to having NUMA spanning enabled and
advantages and disadvantages to having it disabled. For more information about
this, check the References section [1].

vNUMA will be requested via image properties or flavor extra specs. Flavor
extra specs will override the image properties. For more information on how
to request certain NUMA topologies and different use cases, check the
References section [2].

There are a few considerations to take into account when creating instances
with NUMA topology in Hyper-V:

* Hyper-V cannot guarantee CPU pinning. Thus, the nova HyperVDriver will not
  create an instance having the ``hw:cpu_policy`` flavor extra-spec or
  ``hw_cpu_policy`` image property set to ``dedicated``.

* Hyper-V cannot guarantee asymmetric instance NUMA topologies and the nova
  HyperVDriver will not create them. For example, if the instance requires
  2GB memory in NUMA Node 0 and 6GB in NUMA Node 1, the instance will not
  spawn. Same rule applies for the number of vCPUs.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Claudiu Belu <cbelu@cloudbasesolutions.com>

Work Items
----------

As described in the Proposed Change section.

Dependencies
============

None

Testing
=======

* Unit tests.
* New feature will be tested by Hyper-V CI.

Documentation Impact
====================

None

References
==========

[1] Hyper-V Virtual NUMA Overview
  https://technet.microsoft.com/en-us/library/dn282282.aspx

[2] Virt driver guest NUMA node placement & topology
  http://specs.openstack.org/openstack/nova-specs/specs/juno/implemented/virt-driver-numa-placement.html

History
=======

* Approved in Liberty.
* Added Hyper-V related restrictions.
