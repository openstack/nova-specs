..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
PCI Passthrough Groups
==========================================

https://blueprints.launchpad.net/nova/+spec/pci-passthrough-groups

This spec allows operators to create a flavor using a PCI alias to
request a group of PCI devices. These groups of PCI devices are tracked
as a single indivisible unit within Placement. The default custom
resource class used to track these PCI groups is derived from the
PCI group type name, and the name of the inventory is derived from
the PCI group name. The pci_alias config already supports mapping
to a specific placement resource class.

Problem description
===================

Some PCI devices only make sense to be consumed as a group.
When you assign the grouped PCI devices to a VM, all of the
devices in the group as always consumed together by a single VM.
Currently Nova does not understand any grouping other than
NUMA affinity.

While there are some cases where a device could be consumed by
multiple different groups, that are dynamically picked based on
demand, we are ignoring these use cases for now.
In particular, we make the simplifying restriction
that a tracked PCI device can only be a member of a single group,
and when a PCI device is a member of a group, it can only be used
as part of that PCI group.

Use Cases
---------

Some GPUs expose both a graphics physical function and an audio
function. In order to support passing through both devices, we need
to ensure that we pass through a matching pair of devices.
This spec would allow a device group to be created such that
operators configure the matching pairs of audio and graphics
devices, and users can request one (or more) of those pairs via
the usual PCI alias.

Note, we are currently excluding the use case of users requesting
either the pair of devices or just the graphics device, as that
would result in additional complexity that should be considered
in a separate follow on specification.

Let us consider the specific case of the Graphcore C200 device,
where a set of PCI cards are connected together via IPU-Link:
https://docs.graphcore.ai/projects/C600-datasheet/en/latest/product-description.html#ipu-link-cables

Each physical card presents two PCI devices. The card can be used
independently of other cards if a matched pair of devices are
presented to the VM. PCI groups allows this device to be correctly
passed through to VMs by ensuring a matched pair of PCI devices are
always assigned to each VM.

In addition, some servers can be statically configured to group
either two devices, four devices or eight devices as a single group.
These can all be statically configured using PCI group to ensure
we always respect the non-PCI connectivity between those PCI devices.

Proposed change
===============

The key parts of this change include:

* extend `[pci]device_spec` to model groups of PCI devices
* devices are linked by both a group type name, and a specific group name
* the group type name is used to generate a custom resource class,
  i.e. `CUSTOM_PCI_GROUP<group_type_name>`. Note this is just the default
  that changes when you specify a group type name, and it can be
  overrriden by explicitly specifying a different resource_class tag.
* Each group is registered in placement, in a similar way to a device.
  Each group being a separate resource provider with a single inventory
  item for the associated group type custom resource type, with a name
  that is generated from the group_name rather than the PCI device address
* extend `[pci]alias` simply mapps to the resource class mentioned
  above, such as `CUSTOM_PCI_GROUP_<group_type_name>`.
* PCI tracker will have the group_name and group_type_name added to
  each device that is being tracked, such that we can look up a group
  of devices associated with each specific named group tracked
  in placement.

There will be configuration validation checks:

* pci groups are only supported when PCI devices are tracked in placement
* all device groups must have two or more PCI devices
* each physical PCI device can only be in one group,
  and must only be tracked in placement once

For example, lets consider the following PCI devices:

* 4e:00.0 Processing accelerators: Graphcore Ltd Device 0003
* 4f:00.0 Processing accelerators: Graphcore Ltd Device 0003
* 89:00.0 Processing accelerators: Graphcore Ltd Device 0003
* 8a:00.0 Processing accelerators: Graphcore Ltd Device 0003

The two physical cards, spread across two NUMA nodes can be presented
in two possible ways: either two groups or a single group, depending on
the use cases. For example, two separate devices would be:::

    [pci]
    device_spec = {"address": ":4e:00.0", group_name:"graphcore_1", group_type:"c200_x1"}
    device_spec = {"address": ":4f:00.0", group_name:"graphcore_1", group_type:"c200_x1"}
    device_spec = {"address": ":4e:00.0", group_name:"graphcore_2", group_type:"c200_x1"}
    device_spec = {"address": ":4f:00.0", group_name:"graphcore_2", group_type:"c200_x1"}
    alias = {"name":"c200_x1", resource_class:"CUSTOM_PCI_GROUP_C200_X1"}

But exposing the two cards, exposed as four PCI devices,
as a single unit of 4 PCI devices, would look like this:::

    [pci]
    device_spec = {"address": ":4e:00.0", group_name:"graphcore_1", group_type:"c200_x2"}
    device_spec = {"address": ":4f:00.0", group_name:"graphcore_1", group_type:"c200_x2"}
    device_spec = {"address": ":4e:00.0", group_name:"graphcore_1", group_type:"c200_x2"}
    device_spec = {"address": ":4f:00.0", group_name:"graphcore_1", group_type:"c200_x2"}
    alias = {"name":"c200_x2", resource_class:"CUSTOM_PCI_GROUP_C200_X2"}

Alternatives
------------

For some simple cases, NUMA affinity can simulate what is required.
But currently hardware like Graphcore C200 does not work well with Nova.

Data model impact
-----------------

PCI tracker needs to be extended to include group_name and group_type
for each PCI device.

REST API impact
---------------

No impact

Security impact
---------------

No impact

Notifications impact
--------------------

No impact

Other end user impact
---------------------

No impact

Performance Impact
------------------

No impact

Other deployer impact
---------------------

The device spec configuration gets some extra options to help
define groups, and the default resource class changes when you
use the new device_group tags, as discussed above.

Developer impact
----------------

None

Upgrade impact
--------------

Devices that are exposed as a group must be not currently
tracked in placement when starting to expose them as a group.

Once new compute nodes will report the new resoruce classes,
which should naturally gate the need for older compute nodes
to know what to do with the new PCI device configuration.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  johngarbutt

Other contributors:
  nathanharper

Feature Liaison
---------------

Feature liaison:
  gibi?

Work Items
----------

* Update pci device config to support pci groups
* Update PCI device tracker to know about pci groups
* Attach groups of devices when device alias requests
  a resource class that maps to a PCI device group
* Update placement with the avilable resources
  from the described pci groups

Dependencies
============

None

Testing
=======

Add a functional test, similar to vgpu tests.

Documentation Impact
====================

Configuration changes need to be documented correctly.

References
==========

None

History
=======

Optional section intended to be used each time the spec is updated to describe
new design, API or any database schema updated. Useful to let reader understand
what's happened along the time.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2024.1 Caracal
     - Introduced
