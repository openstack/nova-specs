..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
I/O (PCIe) based NUMA scheduling
================================

https://blueprints.launchpad.net/nova/+spec/input-output-based-numa-scheduling

I/O based NUMA scheduling will add support for intelligent NUMA node placement
for guests that have been assigned a host PCI device, avoiding unnecessary
memory transactions

Problem description
===================

Currently it is common for virtualisation host platforms to exhibit multi NUMA
node characteristics.

An optimal configuration would be where the guests assigned PCI device and RAM
allocation are associated with the same NUMA node. This will ensure there is
no cross NUMA node memory traffic.

To reach a remote NUMA node the memory request must traverse the inter CPU
link and use the remote NUMA nodes associated memory controller to access the
remote node. This incurs a latency penalty on remote NUMA node memory access
which is not desirable for NFV workloads.

Openstack needs to offer more fine grained control of NUMA configuration in
order to deliver higher performing, lower latency guest applications. The
default guest placement policy is to use any available pCPU or NUMA node.

Proposed change
===============

Libvirt now provides the numa node a PCI device is associated with, we will
use this information to populate the nova DB. For versions of libvirt that do
not provide this information we will add a fall back mechanism to query the
host for this info.

Logic will be added to nova scheduler to allow it decide on which host is best
able satisfy a guests PCI NUMA node requirements.

Logic, similar to what will be implemented in the nova scheduler will be added
to the libvirt driver to allow it decide on which NUMA node to place the guest.

Alternatives
------------

Libvirt supports integration with a NUMA daemon (numad) that monitors NUMA
topology and usage. It attempts to locate guests for optimum NUMA locality,
dynamically adjusting to changing system conditions.

This is insufficient because we need this intelligence in nova for host
selection and node deployment.

Data model impact
-----------------

The PciDevice model will be extended to add a field identifying the NUMA node
that PCI device is associated with.

numa_node = Column(Integer, nullable=False, default="-1")

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

The benefits of associating a guests PCI device and RAM allocation with the
same NUMA node will provides an optimal configuration that will give improved
I/O throughput and reduced memory latencies, compared with the default libvirt
guest placement policy.

This feature will add some scheduling overhead, but this overhead will deliver
improved performance on the host.

The optimisation described here is dependent on the guest CPU and RAM
allocation being associated with the same NUMA node. This feature is described
in the "Virt driver guest NUMA node placement & topology" blueprint referenced
in the dependency section.

Other deployer impact
---------------------

To use this feature the deployer must use HW that is capable of reporting
numa related info to the OS.

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

The blueprint listed below will define a policy used by the scheduler to decide
on which host to place a guest. We plan to respect this policy while extending
it to add support for a PCI devices NUMA node association.

Virt driver guest NUMA node placement & topology
* https://blueprints.launchpad.net/nova/+spec/virt-driver-numa-placement

The blueprint listed below will support use cases requiring SR-IOV NICs to
participate in neutron managed networks.

Enable a nova instance to be booted up with neutron SRIOV ports
* https://blueprints.launchpad.net/nova/+spec/pci-passthrough-sriov

Testing
=======

Scenario tests will be added to validate these modifications.

Documentation Impact
====================

This feature will not add a new scheduling filter, but as it depends on the bp
mentioned in the dependency section we will need to extend their filter. We
will add documentation as required.

References
==========

Support for NUMA and VCPU topology configuration
* https://blueprints.launchpad.net/nova/+spec/virt-driver-guest-cpu-memory-placement

Virt driver guest NUMA node placement & topology
* https://blueprints.launchpad.net/nova/+spec/virt-driver-numa-placement

Enable a nova instance to be booted up with neutron SRIOV ports
* https://blueprints.launchpad.net/nova/+spec/pci-passthrough-sriov
