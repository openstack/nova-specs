..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
I/O (PCIe) based NUMA scheduling
================================

https://blueprints.launchpad.net/nova/+spec/input-output-based-numa-scheduling

I/O based NUMA scheduling will add support for intelligent NUMA node placement
for guests that have been assigned a host PCI device.

Problem description
===================

Modern servers with two or more processors have a Non Uniform Memory
Architecture (NUMA). This means that there are different memory performance
and latency characteristics when accessing memory directly attached to one
processor than when accessing memory directly attached to another processor in
the same server. Similarly, PCIe I/O devices such as Network Interface Cards
(NICs), can be more closely associated with one processor than another.

The optimal configuration with multi NUMA node platforms is where all host
resources that the guest requires are associated with the same host NUMA node,
this will reduce or remove cross NUMA node memory traffic.

To reach a remote NUMA node the memory request must traverse the inter CPU
link and use the remote NUMA nodes associated memory controller to access the
remote node. This incurs a latency penalty on remote NUMA node memory access.

The default guest placement policy is to use any available physical CPU (pCPU)
from any NUMA node. This blueprint optimises Openstack guest placement by
ensuring that a guest bound to a PCI device is scheduled to run on a NUMA node
that is associated with the guests pCPU and memory allocation.

Use Cases
----------

A guest running workloads requires the use of networking and memory resources
from the host. For the use case where the guests resource requirements fit in
a single NUMA node, an optimally configured system all guest resources should
be associated with the same NUMA node. NFV represents an obvious use case for
when this is particularly important, but there are significant benefits for
other more "traditional" cloud and enterprise workloads.

Project Priority
-----------------

The kilo priorities list is currently not defined. However under the currently
proposed list of priorities it would fall under "Performance".

Proposed change
===============

Extend the PCI device model with a NUMA node field.

Libvirt versions > 1.2.6 will provide the NUMA node of a host PCI device we
will store this information in the nova DB for use during the guest placement
phase.

Extend the PCI device capabilities for libvirt config.

Extend the libvirt driver to capture the PCI devices numa node.

Extend PCI device tracker to track the PCI device NUMA node usage.

Nova scheduling will be enhanced to take consideration of a guests PCI device
requirements and the nodes available for placement.

The NUMA topology filter will be modified to ensure the guest is scheduled on
the requested host NUMA node.

Alternatives
------------

Libvirt supports integration with a NUMA daemon (numad) that monitors NUMA
topology and usage. It attempts to locate guests for optimum NUMA locality,
dynamically adjusting to changing system conditions. This is insufficient
because we need this intelligence in nova for host selection and node
deployment.

Data model impact
-----------------

The PciDevice model will be extended to add a field identifying the NUMA node
that PCI device is associated with.

numa_node = Column(Integer, nullable=True)

A DB migration script will use ALTER_TABLE to add a new column to the
pci_devices table in nova DB.

REST API impact
---------------

There will be no change to the REST API.

Security impact
---------------

This blueprint does not introduce any new security issues.

Notifications impact
--------------------

This blueprint does not introduce new notifications.

Other end user impact
---------------------

This blueprint adds no other end user impact.

Performance Impact
------------------

Associating a guests PCI device and RAM allocation with the same NUMA node
provides an optimal configuration that will give improved I/O throughput and
reduced memory latencies, compared with the default libvirt guest placement
policy.

This feature will add some scheduling overhead, but this overhead will deliver
improved performance on the host.

Other deployer impact
---------------------

To use this feature the deployer must use HW that is capable of reporting
NUMA related info to the OS.

Developer impact
----------------

This blueprint will have no developer impact.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    James Chapman

Other contributors:
    Przemyslaw Czesnowicz
    Sean Mooney
    Adrian Hoban

Work Items
----------

* Add a NUMA node attribute to the pci_device object
* Use libvirt to discover hosts PCI device NUMA node association
* Enable nova compute synchronise PCI device NUMA node associations with nova
  DB
* Enable libvirt driver configure guests with requested PCI device NUMA node
  associations
* Enable the nova scheduler decide on which host is best able to support
  a guest
* Enable libvirt driver decide on which NUMA node to place a guest

Dependencies
============

The dependencies for this feature have been included in the Juno release.

Testing
=======

Unit tests will be added to validate these modifications.

Documentation Impact
====================

This feature will not add a new scheduling filter, but rather extend the
existing NUMA topology filter. We will add documentation as required.

References
==========

None
