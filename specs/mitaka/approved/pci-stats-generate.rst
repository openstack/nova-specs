..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
On-demand Generate PCI Device Pools
===================================

https://blueprints.launchpad.net/nova/+spec/pci-stats-generate

This proposal is to generate PCI device pool information on-the-fly instead of
storing the summary pool information in the database.

Problem description
===================

The `compute_nodes` table currently stores in the `pci_stats` field a JSON
representation of PCI device "pools". This information is updated by the
nova-compute resource tracker by the `nova.pci.stats.PciDevStats` class and
read by the Nova scheduler in each iteration of the `select_destinations()`
call when the `nova.objects.ComputeNodeList.get_all()` method is used to pull
all information about compute nodes in the system. The reason that this summary
information is pulled by the scheduler is to avoid having to send message
containing thousands of PCI device records across the wire.

The problem with storing this summary information in the `compute_nodes` table
is two-fold:

1) There is the possibility that the summary information can get out of sync
with the non-summary information stored in the `pci_devices` table, and

2) It interferes with our efforts to represent all resources in the system in a
consistent and generic fashion (the resource-objects blueprint work)

Use Cases
----------

As a developer of Nova, I want to be able to represent all quantitative
resources in the system in a consistent and generic fashion. As an operator, I
do not want summary and detail information in my database to get out of sync.

Proposed change
===============

We propose the following changes to the Nova code base:

1) Temporarily duplicate the logic of
`nova.pci.stats.PciDevStats.supports_request()` method into the
`nova.objects.PciDevicePoolList` object.

2) Move the logic for determining if a compute node can provide a requested PCI
device to an instance from the `nova.pci.stats.PciDevStats.consume_requests()`
method to the `nova.pci.manager.PciDevTracker._claim_for_instance()` method.

3) Modify the `nova.objects.ComputeNode` object to load on-demand the
`pci_device_pools` field by a subquery instead of pulling from the
`compute_nodes.pci_stats` field in the database. The `PciDevicePoolList` object
can be generated using a single SQL query on the `pci_devices` table, like so::

    SELECT product_id, vendor_id, numa_node, COUNT(*) as count
    FROM pci_devices
    WHERE compute_node_id = ?
    GROUP BY product_id, vendor_id, numa_node;

This will only be used for legacy compute nodes that rely on the
`nova.objects.ComputeNode.pci_device_pools` field attribute.

4) Change the scheduler's host manager to load PCI device pool information
using a new `nova.objects.PciDevicePoolList.get_all` method that returns all
PCI device pool information for all compute nodes, but only when the
PciPassthroughFilter is enabled. This will match how the HostAggregate
information is loaded by the scheduler and collated to HostState objects.

The SQL statement for grabbing all of the PCI device pool information for
compute nodes looks like this::

    SELECT compute_node_id, product_id, vendor_id, numa_node, COUNT(*) as count
    FROM pci_devices
    GROUP BY compute_node_id, product_id, vendor_id, numa_node;

5) Change the `nova.scheduler.pci_passthrough_filter.host_passes` method to use
the `nova.objects.PciDevicePoolList.supports_requests()` method instead of the
`nova.pci.stats.PciDevStats.support_requests()` method.

6) Remove the `nova.pci.stats` module entirely.

7) Deprecate the `compute_node.pci_stats` field in the database and mark it for
removal in the N release.

Alternatives
------------

None.

Data model impact
-----------------

None, this changes the implementation of existing model definitions only.

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

None.

Performance Impact
------------------

None. The over-wire information will continue to be the same. The database
query for generating the summary PCI device information should be very quick.

Other deployer impact
---------------------

None.

Developer impact
----------------

This will allow the resource-objects blueprint to proceed, since PCI device
resources will be able to be handled in the same way as NUMA or other
quantitative resources.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dstepanenko

Other contributors:
  jaypipes

Work Items
----------

1) Duplicate supports_request() method into the
`nova.objects.PciDevicePoolList` object.

2) Move `nova.pci.stats.PciDevStats.consume_requests()`
to the `nova.pci.manager.PciDevTracker._claim_for_instance()` method.

3) Modify the `nova.objects.ComputeNode` object to load on-demand the
`pci_device_pools` field

4) Change the scheduler host manager to load PciDevicePoolList object for all
compute nodes in the same way that host aggregate information is loaded, and
only when the PciPassthroughFilter is enabled.

5) Change the `nova.scheduler.pci_passthrough_filter.host_passes` method to use
the `nova.objects.PciDevicePoolList.supports_requests()` method

6) Remove the `nova.pci.stats` module entirely.

7) Annotate the `nova.db.sqlalchemy.models.ComputeNode.pci_stats` field in the
database as deprecated.

Dependencies
============

None.

Testing
=======

Should be a net reduction in unit tests since the logic for decrementing the
PCI device pool counts will be removed entirely.

Documentation Impact
====================

None. No user-facing changes.

References
==========

None.

History
=======

None.
