..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Libvirt Slices
==========================================

https://blueprints.launchpad.net/nova/+spec/libvirt-slices

In this spec we allow operators to define flavors that
map to a set of predefined libvirt XML templates,
allowing for careful optimized NUMA placement of all
resources given to each guest.

Problem description
===================

Operators of clouds with performance optimized flavors spend
a lot of time trying to persuade Nova to make the exact set
of resource placements they would like.

Small mistakes in this process of optimizing the various
schedulers quickly lead to confusing behaviors to debug and
often bad packing of resources within the hypervisor.

From a Nova point of view, there is a large explosion of
possible combinations each hardware type can support,
particularly as the number of cores, NUMA zones, and
device types increase.

Use Cases
---------

For clouds with performance sensitive workloads, it is common
to have multiple groups of flavors targeting different
groups of hosts. For example, you often have some hosts
configured for maximum performance and a different group of
host configured configured to support higher VM density
(e.g. overcommitment of CPU resources).

This spec is focused around a group of hosts where the
operator is aiming for maximum performance.

When creating flavors for maximum performance,
typically there are a small number of flavors,
e.g. 1/8th, 1/4th, 1/2 and full host VMs.
The operator wants to ensure that each VM gets the best
performance possible, ideally in isolation from all other
VMs on the hypervisor.

Lets consider the case where you have a host that contains
eight PCI attached accelerators (e.g. GPU, TPU, etc).
The operator would like to support three sizes of instances
on this host, one that get one accelerator, another that
gets all eight accelerators, and a final size that gets
four accelerators.
In addition, there is a single ethernet network card
that requires SR-IOV virtual functions to be
passed through to each VM.

While it would be simpler to consider the case when all
available XML templates are mutually exclusive, it is
impractical to operate a cloud with such a restriction.
For this version, we only allow overlapping templates
where there is a clear parent child relationship.

For example, lets consider the eight GPU host. It has
a root template that has all eight GPUs attached.
There are two child templates, each with four GPUs attached.
For each of the four GPU templates, there are four child
templates that each have one GPU attached.

In addition, we should consider the likely future
case of HBM memory flat mode, where CPU cores are in
two different NUMA zones at the same time.

Proposed change
===============

There are several parts to the proposed change:

* Configuration of the slices on the hypervisor
* Reporting the slices to placement
* Requesting a slice within a flavor
* Mixing slices and regular flavors on a single host
* Changes to libvirt driver to use slice template,
  rather than typical dynamic xml generation.
* Changes to NUMATopologyFilter and PciPassthroughFilter

Configuration of the slices
---------------------------

An example configuration for the eight GPU host
the libvirt slices config would look something like:::

    [libvirt]
    slice_spec = {name="8_1", "resource_class":"CUSTOM_SLICE_8_GPU_V1", template_file": "/etc/nova/slice_8_1_gpus.xml"}
    slice_spec = {name="4_1", "resource_class":"CUSTOM_SLICE_4_GPU_V1", template_file": "/etc/nova/slice_4_1_gpus.xml", conflict_parent="8_1"}
    slice_spec = {name="4_2", "resource_class":"CUSTOM_SLICE_4_GPU_V1", template_file": "/etc/nova/slice_4_2_gpus.xml", conflict_parent="8_1"}
    slice_spec = {name="1_1", "resource_class":"CUSTOM_SLICE_1_GPU_V1", template_file": "/etc/nova/slice_1_1_gpus.xml", conflict_parent="4_1"}
    slice_spec = {name="1_2", "resource_class":"CUSTOM_SLICE_1_GPU_V1", template_file": "/etc/nova/slice_1_2_gpus.xml", conflict_parent="4_1"}
    ...
    slice_spec = {name="1_8", "resource_class":"CUSTOM_SLICE_1_GPU_V1", template_file": "/etc/nova/slice_1_8_gpus.xml", conflict_parent="4_2"}

TODO: need to model pci devices here for the SR-IOV attach case.
Need to describe how the pci device requests are interpreted here.

Reporting slices to placement
-----------------------------

The slices are reported to placement as a new resource provider
that is a child of the compute node resource provider.
This is similar to how PCI devices are modeled in placement.

If the slice spec specifies a conflict_parent, then the resource
provider associated with that slice is used as the parent device.

Requesting a slice within a flavor
----------------------------------

Lets take the 4 GPU flavor, we can describe it as closely as possible
to what would be used with dynamic XML generation.
If pinned CPUs and huge pages are being used, it is best to
specify these in the flavor for informational purposes.

We then add extra specs similar to a baremetal instance, where we
request zero resources for VCPU, PCPU, MEMORY_MB, and DISK_GB.
In addition we add requests for the matching custom resource classes,
so for a 4 GPU flavor, we would requests 4 of CUSTOM_SLICE_1_GPU_V1
and 1 of CUSTOM_SLICE_4_GPU_V1

Mixing slices and regular flavors on a single host
--------------------------------------------------

For this first version, a host configured with slices will not report
any other resources used by the dynamic xml generation.

It would be possible, in theory, to have non-overlapping resources
between the slice specifications and the CPU shared and dedicated sets.

Changes to libvirt driver to use slice templates
------------------------------------------------

The xml templates are in a jinja2 format.


Changes to the NUMATopologyFilter and PciPassthroughFilter
----------------------------------------------------------

TODO

Alternatives
------------

The alternative is to continue to have add special logic for each of the
different types of affinity and NUMA passthrough that could model the
general case, e.g. PCI device NUMA passthrough.

Data model impact
-----------------

The slices will be tracked in the database, using the tables used by PCI devices.

REST API impact
---------------

No impact.

Security impact
---------------

No impact.

Notifications impact
--------------------

No impact.

Other end user impact
---------------------

No impact.

Performance Impact
------------------

This should remove some of the explosion of possible combinations
that we see in complex NUMA and PCI passthrough cases.

In addition, careful curation of the XML should allow operators
to get the best performance possible from their hardware.

Other deployer impact
---------------------

There could be future work to help generate and/or validate
XML templates against specific hardware?

Existing use cases should not be affected.

Developer impact
----------------

No impact.

Upgrade impact
--------------

The feature only works once hypervisors report
slices to placement, which should allow for a gradual
rollout across empty hypervisors.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  johnthetubaguy

Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  None

Work Items
----------

TODO

Dependencies
============

None


Testing
=======

TODO


Documentation Impact
====================

TODO

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2024.2 Dalmatian
     - Introduced
