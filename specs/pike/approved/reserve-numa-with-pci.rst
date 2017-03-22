..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Reserve NUMA nodes with PCI devices attached
============================================

https://blueprints.launchpad.net/nova/+spec/reserve-numa-with-pci

Since Juno, instances bound with PCI devices must be scheduled to at least one
NUMA node associated with the PCI device [1]_. Unfortunately, the scheduler was
not enhanced to ensure instances without a PCI device would not occupy NUMA
nodes unnecessarily. This spec proposes to optimize the scheduler to ensure
these NUMA nodes are reserved, thus increasing the number of PCI-attached
instances deployers can boot in conjunction with non-PCI instances.


Problem description
===================

The NUMA locality of I/O devices is an important characteristic to consider
when configuring a high performance, low latency system for NFV workloads. The
'I/O (PCIe) Based NUMA Scheduling' blueprint optimized instance placement by
ensuring that scheduling of instances bound to a PCI device, via PCI
passthrough requests, is optimized to ensure NUMA node co-location for PCI
devices and CPUs. However, the scheduler uses nodes linearly, even when there
are only a select few of these many nodes associated with special resources
like PCI devices. As a result, instances without any PCI requirements can fill
host NUMA nodes with PCI devices attached, which results in scheduling failures
for PCI-bound instances.

Use Cases
---------

* As an operator, I want to reserve nodes with PCI devices, which are typically
  expensive and very limited resources, for guests that actually require them.

* As a user launching instances that require PCI devices, I want the cloud to
  ensure that they are available.

Proposed change
===============

Enhance both the filter scheduler and resource tracker to prefer non-PCI NUMA
nodes for non-PCI instances.

If an instance is bound to a PCI device, then existing behavior dictates that
the NUMA node associated with the PCI device will be used at a minimum.

If an instance is not bound to a PCI device, then hosts without PCI devices
will be preferred. If no host matching this and other requirements exists, then
hosts with PCI devices will be used but NUMA nodes without associated PCI
devices will be preferred.

Instances with PCI devices must still be scheduled on nodes with a PCI device
attached. Enabling some sort of "soft affinity" where this is no longer a
requirement is outside of the scope of this blueprint.

Alternatives
------------

* Add a configuration option that allows instances to schedule to nodes other
  than those associated with the PCI device(s). This will ensure instances can
  fully utilize resources, but will not solve the problem of non-PCI instances
  occupying preferred NUMA nodes. This should be seen as a complement, rather
  than an alternative.

* Ensure PCI devices are placed in PCI slots associated with the
  highest-numbered NUMA node. PCI-based instances will always use these, while
  non-PCI instances are assigned to node linearly (and therefore, lowest
  first). However, this would mean moving tens or even thousands of PCI devices
  and would require a spreading, rather than packing, based approach to host
  scheduling.

* Use host aggregates instead. This doesn't require any new functionality but
  it will fail in the scenario where a host does not have uniform PCI
  availability across all nodes or where instances consume all PCI devices on a
  host but not all CPUs. In both cases, a given amount of resources on said
  hosts will go to waste

Data model impact
-----------------

None.

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

An additional weigher will be added, which will assess the number of PCI
devices on each node of a host. This will result in an slight increase in
latency during filtering. However, this impact will be negligible compared to
the performance enhancement that of using correctly-affinitized PCI devices
brings, nor the cost saving incurred from fully utilizing all available
hardware.

Other deployer impact
---------------------

The PCI weigher will be added to ``nova.scheduler.weights.all_weighers``.
However, deployers may wish to enable this manually using the
``filter_scheduler.weight_classes`` configuration option.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sfinucan

Work Items
----------

* Add a new ``PCIWeigher`` weigher class to prefer hosts without PCI devices
  when there are no PCI devices attached to the instance and vice versa

* Modify scheduling code to prefer cores on NUMA nodes without attached PCI
  devices when there are no PCI devices attached to the instance

Dependencies
============

None.

Testing
=======

* Unit tests

* Functional test which fake out libvirt resource reporting but will actually
  test the scheduler

Documentation Impact
====================

A new weigher will be added. This should be documented.

References
==========

The 'I/O (PCIe) Based NUMA Scheduling' blueprint

* https://blueprints.launchpad.net/nova/+spec/input-output-based-numa-scheduling

.. [1] https://specs.openstack.org/openstack/nova-specs/specs/juno/approved/input-output-based-numa-scheduling.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
