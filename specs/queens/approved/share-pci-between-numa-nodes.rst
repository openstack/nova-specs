..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================
PCI NUMA Policies
=================

https://blueprints.launchpad.net/nova/+spec/share-pci-between-numa-nodes

In the Juno release the "I/O based NUMA scheduling" spec was implemented [1]_.
This modified the scheduling algorithm such that users were only allowed to
boot instances with PCI devices if the instance was being scheduled on at least
one of the NUMA nodes associated with the PCI devices or if the PCI devices
had no information about NUMA nodes and PCI devices affinity. Before this,
nova booted instances with PCI devices without checking NUMA affinity. However,
such hard-coded behaviour causes problems if not every NUMA node has its own
PCI device. In this case nova wouldn't allow booting an instance on NUMA nodes
without PCI devices.

Problem description
===================

In its current iteration, nova boots instances with PCI devices on the same
NUMA nodes that these PCI devices are associated with. This is good for
performances, as it ensures there is limited cross-NUMA node memory traffic.
However, if a user has an environment with two NUMA nodes and only one PCI
device (for example SR-IOV card associated with first NUMA node) they would be
able to boot instance with *one* NUMA node and SR-IOV ports only on the first
NUMA node. In this case, the user cannot use half of the CPUs and RAM because
these resources are placed on second NUMA node. The user should be able to boot
instances on different NUMA nodes, even if it makes performance worse.

In addition, the current behavior doesn't always provide the best performance
solution because an instance can use a PCI device if there is no information
about affinity of NUMA nodes with this PCI device. This can lead to a situation
whereby PCI device is not on the NUMA node which the CPU and RAM is on. The
scheduling mechanism should be more flexible. The user should be able to choose
between maximum performance behavior and maximum chance of successfully
launching the instance.

Of course this ability should be configurable and the current scheduling
behaviour must remain as the default.

Use Cases
---------

- As an operator who cares about obtaining maximum performance from my PCI
  devices, I want to ensure my PCI devices are always NUMA affinitized, even
  if this results in lower resource usage.

- As an operator who cares about maximum usage of resources, I want to ensure
  that an instance has the best chance of being scheduled successfully, even if
  this results in slightly lower performance for some instances.

- As an operator of a deployment with a mix of NUMA-aware and non-NUMA-aware
  hosts, I want to ensure my PCI devices are always NUMA affinitized *if NUMA
  information is available*. However, I still want to be able to schedule
  instances of the non-NUMA-aware hosts.

  Alternatively, as an operator with an existing deployment using PCI devices,
  I don't want nova to pull the rug from under my feet and suddenly refuse to
  schedule to hosts with no NUMA information when it used to.

Proposed change
===============

This spec is needed to decide which PCI device will be used by a new instance.
To this end, we will add a new flavor extra spec
``hw:pci_numa_affinity_policy`` and image metadata
``hw_pci_numa_affinity_policy``. They will have one of three values.

**required**

  This value will mean that nova will boot instances with PCI devices *only* if
  at least one of the NUMA nodes is associated with these PCI devices. It means
  that if NUMA node info for some PCI devices could not be determined, those
  PCI devices wouldn't be consumable by the instance. This provides maximum
  performance.

**preferred**

  This value will mean that `nova-scheduler` will choose a compute host with
  minimal consideration for the NUMA affinity of PCI devices. `nova-compute`
  will attempt a best effort selection of PCI devices based on NUMA affinity,
  however, if this is not possible then `nova-compute` will fall back to
  scheduling on a NUMA node that is not associated with the PCI device.

  Note that even though the ``NUMATopologyFilter`` will not consider NUMA
  affinity, the weigher proposed in the *Reserve NUMA Nodes with PCI Devices
  Attached* spec [2]_ can be used to maximize the chance that a chosen host
  will have NUMA-affinitized PCI devices.

**legacy**

  This is the default value and it describes the current nova behavior. Usually
  we have information about association of PCI devices with NUMA nodes.
  However, some PCI devices do not provide such information. The ``legacy``
  value will mean that nova will boot instances with PCI device if either:

  * The PCI device is associated with at least one NUMA nodes on which the
    instance will be booted

  * There is no information about PCI-NUMA affinity available

  This is required because the configuration option will apply globally to an
  instance which may have multiple devices attached, and not all of these
  devices may have NUMA affinity. An example of such a device is the FPGAs
  integrated on to the dies of recent Intel Xeon chips, which hook into the QPI
  bus and therefore have no NUMA affinity [3]_.

If both image and flavor properties are not set (equals ``None``) the
``legacy`` policy will be used. If one of image *or* flavor property is not set
(equals ``None``) but the other property is set then the value of the set
property will be used. In a case of conflicts between flavor and image
properties (both properties are set and they are not equal) an exception will
be raised.

Alternatives
------------

- Change placement behavior to *not* boot instances which do not need PCI
  devices on NUMA nodes with PCI devices. This would maximize the possibility
  that an instance that requires PCI devices could find a suitable host to boot
  on. However, it would severely limit our flexibility as attempting to boot
  many instances without PCI devices would result in a large number of unused,
  PCI device-having hosts. Furthermore, once all non-PCI-having NUMA nodes are
  saturated, deploys of non-PCI-needing instances would fail.

- Change placement behavior to *avoid* booting instances without PCI devices on
  NUMA nodes with PCI devices *if possible*. This is a softer version of the
  first alternative and has actually been addressed by the
  'reserve-numa-with-pci' spec [4]_.

- Make the PCI NUMA strictness part of the individual PCI device request. This
  would allow us to represent requests like "I need to be strictly affined to
  this NIC, but I don't need to be strictly affined to this FPGA". It is very
  unlikely that this level of granularity of request would be required. In
  addition, it's difficult to see how this would fit into the resource provider
  world in the future as the problem is transformed from a scheduling one (at
  the host level) to a placement one.

Data model impact
-----------------

A new field, ``pci_numa_affinity_policy``, will be added to the
``InstanceNUMACell`` object. As this object is stored as a JSON blob in the
database, no DB migrations are necessary to add the new field to this object.

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

If the ``required`` policy is selected, the performance of instances with PCI
devices will be more consistent in deployments with non-NUMA aware compute
hosts present. This is because nova would no longer use these hosts. However,
this will also result in a smaller number of hosts available on which to
schedule instances. If all hosts correctly provide NUMA information,
performance will be unchanged.

If the ``preferred`` policy is selected, the performance of instances with PCI
devices may be worse for some instances. This would be because nova can now
schedule an instance on a host with non-NUMA-affinitized PCI devices. However,
this will also result in a larger number of hosts available on which to
schedule instances, maximizing flexibility for operators who don't require
maximum performance. The PCI weigher proposed in the *Reserve NUMA Nodes with
PCI Devices Attached* [2]_ can be used to minimize the risk of performance
impacts.

If the ``legacy`` policy is selected, the existing nova behaviour will be
retained and performance will remain unchanged.

From a scheduling perspective, this may introduce a delay if the ``required``
policy is selected and there are a large number of hosts with PCI devices that
do not report NUMA affinity. On the other hand, using the ``preferred`` policy
will result in improved performance as the ability to schedule is no longer
tied to the availability of a free CPUs on a NUMA node associated with the PCI
device.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Stephen Finucane (stephenfinucane)

Other contributors:
    Sergey Nikitin (snikitin)

Work Items
----------

* Add new spec to the flavor
* Add new field to the InstanceNUMACell object
* Change the process of NUMA node choosing, considering new policy
* Update user docs

Dependencies
============

None

Testing
=======

Scenario tests will be added to validate these modifications.

Documentation Impact
====================

This feature will not add a new scheduling filter, but it will change the
behaviour of NUMATopologyFilter. We should add documentation to describe new
flavor extra spec and image metadata.

References
==========

.. [1] https://specs.openstack.org/openstack/nova-specs/specs/juno/approved/input-output-based-numa-scheduling.html
.. [2] https://specs.openstack.org/openstack/nova-specs/specs/pike/approved/reserve-numa-with-pci.html
.. [3] https://www.ece.cmu.edu/~calcm/carl/lib/exe/fetch.php?media=carl15-gupta.pdf
.. [4] https://blueprints.launchpad.net/nova/+spec/reserve-numa-with-pci

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
