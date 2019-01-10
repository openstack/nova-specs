..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.
 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Neutron SR-IOV Port Live Migration
==================================

https://blueprints.launchpad.net/nova/+spec/libvirt-neutron-sriov-livemigration

When nova was extended to support SR-IOV by [0]_, live migration was not
directly addressed as part of the proposed changes. As a result while
live migration with SR-IOV is technically feasible, it remains unsupported
by the libvirt driver. This spec seeks to address this gap in live migration
support for the libvirt virt driver.


Problem description
===================

Live Migration with SR-IOV devices has several complicating factors.

*     NUMA affinity
*     hardware state
*     SR-IOV mode
*     resource claims

NUMA affinity is out of the scope of this spec and will be addressed
separately by [1]_.

The SR-IOV mode of a neutron port directly impacts how a live migration
can be done. This spec will focus on the two categories of SR-IOV primarily,
direct passthrough (``vnic_type=direct|direct-physical``) and indirect
passthrough (``vnic_type=macvtap|virtio-forwarder``). For simplicity, direct
mode and indirect mode are used instead of ``vnic_type`` in the rest
of the spec.

When a device is exposed to a guest via direct mode SR-IOV, maximum
performance is achieved at the cost of exposing the guest to the
hardware state. Since there is no standard mechanism to copy the hardware
state, direct mode SR-IOV cannot be conventionally live migrated.
This spec will provide a workaround to enable this configuration.

Hardware state transfer is a property of SR-IOV live migration that cannot
be addressed by OpenStack, as such this spec does not intend to copy hardware
state. Copying hardware state requires explicit support at the hardware,
driver and hypervisor level which does not exist for SR-IOV devices.

.. note:: hardware state in this context refers to any NIC state such as
          offload state or Tx/Rx queues that are implemented in hardware
          which is not software programmable via the hypervisor e.g. MAC
          address is not considered hardware state in this context as
          libvirt/qemu can set the MAC address of an SR-IOV device via
          a standard host level interface.

For SR-IOV indirect mode, the SR-IOV device is exposed via a software
mediation layer such as macvtap + kernel vhost, vhost-user or vhost-vfio.
From a guest perspective, the SR-IOV interfaces are exposed as virtual NICs
and no hardware state is observed. Indirect mode SR-IOV therefore allows
migration of guests without any workarounds.

The main gap in SR-IOV live migration support today is resource claims.
As mentioned in the introduction it is technically possible to live migrate
a guest with an indirect mode SR-IOV device between two hosts today, however,
when you do, resources are not correctly claimed. By not claiming the SR-IOV
device an exception is raised after the VM has been sucessfully migrated to the
destination in the post migration cleanup.

When live migrating today, migration will also fail if the PCI mapping is
required to change. Said another way, migration will only succeed if there is
a free PCI device on the destination node with the same PCI address as the
source node that is connected to the same physnet and is on the same NUMA
node.

This is because of two issues. Firstly, nova does not correctly claim the
SR-IOV device on the destination node and second, nova does not modify
the guest XML to reflect the host PCI address on the destination.

As a result of the above issues, SR-IOV live migration in the libvirt driver
is currently incomplete and incorrect even when the VM is successfully
moved.


Use Cases
---------

As a telecom operator with stateful VNF such as a vPE Router
that has a long peering time, I would like to be able to utilise
direct mode SR-IOV to meet my performance SLAs but desire the
flexibility of live migration for maintenance. To that end, as an operator,
I am willing to use a bond in the guest to a vSwitch or indirect SR-IOV
interface to facilitate migration and retain peering relationships while
understanding performance SLAs will not be met during the migration.

As the provider of a cloud with a hardware offloaded vSwitch that leverages
indirect mode SR-IOV, I want to offer the performance it enables to my
customers but also desire the flexibility to be able to transparently migrate
guests without disrupting traffic to enable maintenance.

Proposed change
===============

This spec proposes addressing the problem statement in several steps.

Resource claims
---------------

Building on top of the recently added multiple port binding feature this
spec proposes to extend the existing ``check_can_live_migrate_destination``
function to claim SR-IOV devices on the destination node via the PCI resource
tracker. If claiming fails then the partially claimed resources will be
released and ``check_can_live_migrate_destination`` will fail. If the claiming
succeeds the ``VIFMigrateData`` objects in the ``LiveMigrateData`` object
corresponding to the SR-IOV devices will be updated with the destination
host PCI address. If the migration should fail after the destination resources
have been claimed they must be released in the
``rollback_live_migration_at_destination`` call. If the migration succeeds
the source host SR-IOV device will be freed in ``post_live_migration``
(clean up source) and the state of claimed devices on the destination are
updated to allocated. By proactively updating the resouce tracker in both the
success and failure case we do not need to rely on the
``update_available_resource`` periodic task to heal the allocations/claims.


SR-IOV Mode
-----------

Indirect Mode
~~~~~~~~~~~~~

No other nova modifications are required for indirect mode SR-IOV
beyond those already covered in the Resouce claims sechtion.

Direct Mode
~~~~~~~~~~~

For direct mode SR-IOV, to enable live migration the SR-IOV devices must
be first detached on the source after ``pre_live_migrate`` and then
reattached in ``post_live_migration_at_destination``.

This mimics the existing suspend [2]_ and resume [3]_ workflow whereby
we workaround QEMUs inability to save device state during a suspend
to disk operation.

.. note:: If you want to maintain network connectivity during the
          migration, as the direct mode SR-IOV device will be detached,
          a bond is required in the guest to a transparently live migratable
          interface such as a vSwitch interface or a indirect mode SR-IOV
          device. The recently added ``net_fallback`` kernel driver is out
          of scope of this spec but could also be used.


XML Generation
--------------

Indirect mode SR-IOV does not encode the PCI address in the libvirt XML.
The XML update logic that was introduced in the multiple port bindings
feature is sufficent to enable the indirect use case.

Direct mode SR-IOV does encode the PCI address in the libvirt XML, however,
as the SR-IOV devices will be detached before migration and attached after
migration no XML updates will be required.


Alternatives
------------

* As always we could do nothing and continue to not support live migration
  with SR-IOV devices. In this case, operators would have to continue
  to fall back on cold migration. As this alternative would not fix the
  problem of incomplete live migration support additional documentation or
  optionally a driver level check to reject live migration would be warranted
  to protect operators that may not be aware of this limitation.

* We could add a new API check to determine if an instance has an SR-IOV
  port and explicitly fail to migrate in this case with a new error.


Data model impact
-----------------

It is expected that no data model changes should be required as the existing
VIF object in the ``migration_data`` object should be able to store the
associated PCI address info. If this is not the case a small extension to
those objects will be required for this info.


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

Users of direct mode SR-IOV should be aware that auto hotplugging
is not transparent to the guest in exactly the same way that
suspend is not transparent today. This will be recorded in the release
notes and live migration documentation.


Performance Impact
------------------

This should not significantly impact the performance of a live migration.
A minor overhead will be incurred in claiming the resource and updating the XML

Other deployer impact
---------------------

SR-IOV live migration will be enabled if both the source and dest node support
it. If either compute node does not support this feature the migration will
be aborted by the conductor.

Developer impact
----------------

None

Upgrade impact
--------------

This feature may aid upgrade of hosts with SR-IOV enabled
guests in the future by allowing live migration to be used
however, as that will require both the source and dest node to
support SR-IOV live migration first.
As a result, this feature, will have no impact for this release.

To ensure cross version compatiblity
the conductor will validate if the source and destination nodes
support this feature following the same pattern that is used
to detect if multiple port binding is supported.

When upgrading from stein to train the conductor check
will allow this feature to be used with no operator intervention
required.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sean-k-mooney

Other contributors:
  adrian.chiris

Work Items
----------

- Spec: Sean-K-Mooney
- PCI resource allocation and indirect live-migration support: Adrianc
- Direct live-migration support: Sean-K-Mooney

Dependencies
============

This spec has no dependencies but intends to collaborate with the
implementation of NUMA aware live migration [1]_

Note that modification to the sriovnicswitch ml2 driver may
be required to support multiple port bindings. This work if needed
is out of scope of this spec and will be tracked using Neutron
RFE bugs and/or specs as required.

Testing
=======

This feature will be tested primarily via unit and functional tests,
as SR-IOV testing is not available in the gate tempest test will not
be possible. Third party CI could be implemented but that is not part
of the scope of this spec. The use of the netdevsim kernel module to allow
testing of SR-IOV without SR-IOV hardware was evaluated. While the netdevsim
kernel module does allow the creation of an SR-IOV PF netdev and the
allocation of SR-IOV VF netdevs, it does not simulate PCIe devices.
As a result in its current form the netdevsim kernel module cannot be used
to enable SR-IOV testing in the gate.

Documentation Impact
====================

Operator docs will need to be updated to describe the new feature
and specify that direct mode auto-attach is not transparent to the guest.

References
==========

.. [0] https://specs.openstack.org/openstack/nova-specs/specs/juno/implemented/pci-passthrough-sriov.html
.. [1] https://review.openstack.org/#/c/599587/2/specs/stein/approved/numa-aware-live-migration.rst
.. [2] https://github.com/openstack/nova/blob/2f635fa914884c91f3b8cc78cda5154dd3b43305/nova/virt/libvirt/driver.py#L2912-L2920
.. [3] https://github.com/openstack/nova/blob/2f635fa914884c91f3b8cc78cda5154dd3b43305/nova/virt/libvirt/driver.py#L2929-L2932

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Proposed
