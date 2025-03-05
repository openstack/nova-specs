..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================================================
Live migrate VFIO devices using kernel variant drivers
=============================================================================

https://blueprints.launchpad.net/nova/+spec/migrate-vfio-devices-using-kernel-variant-drivers

This spec outlines the necessary steps to live migrate SR-IOV devices
using the new kernel VFIO SR-IOV variant driver interface.

Problem description
===================

Support for devices using the variant driver interface is detailed in this
`specification`__.

However, the migration process is not covered there.
This is addressed in the following section, which describes the Nova updates
required  for SRIOV devices using VFIO SR-IOV variant driver to be live
migrated to other hosts supporting the same devices.

.. __: https://specs.openstack.org/openstack/nova-specs/specs/2025.1/approved/enable-vfio-devices-with-kernel-variant-drivers.html

Use Cases
---------

- As an operator, I want to live migrate VMs with SR-IOV devices if such
  operation is supported by the variant driver.
- As an operator, I want to declare whether a device is live migratable or
  non-live migratable.
- As an operator, I want to define flavors that use live migratable or
  non-live migratable devices.


Proposed change
===============

Description:
------------

Configuring PCI device specification:
*************************************

Administrator must specify whether the device is eligible for live migration to
a similar device on another compute node.

The proposed solution is to add a ``live_migratable`` tag to the device
specification in [pci]dev_spec config.

- ``live_migratable='yes'`` means that the device can be live migrated.
- ``live_migratable='no'`` means that the device cannot be live migrated.

When this tag is encountered by the `PCI resource tracker`__, the
corresponding information will be stored in the respective PciDevice
object under the extra_info field.

- If not specified, the default behavior will be equivalent to
  live_migratable='no'. However, this value will not be persisted in the
  PciDevice object.

.. note::

  The PciDevice object version remains unchanged.

Additionally, if pci in placement is enabled and ``live_migratable='yes'``,
it will record a new standard trait, HW_PCI_LIVE_MIGRATABLE, in the resource
provider representing the physical device. While this trait will not be
utilized by the migration flow, it can serve as a reference for inventory
and later the PCI in Placement code path can be extended to automatically
request this trait if the PCI alias requests ``live_migratable=yes`` device(s).

.. note::

  Since this is not mandatory for the migration, it will be included in
  separate commits.


Configuring PCI aliases:
************************

Users must specify whether the PCI request, and consequently the flavor,
requires a live migratable device.


The proposed solution is to add a new ``live_migratable`` key to the PCI alias
definition in the [pci]alias config.

- ``live_migratable='yes'`` means that the user wants a device(s) allowing live
  migration to a similar device(s) on another host.
- ``live_migratable='no'`` This explicitly indicates that the user requires a
  non-live migratable device, making migration impossible.
- If not specified, the default is ``live_migratable=None``, meaning that
  either a live migratable or non-live migratable device will be picked
  automatically. However, in such cases, migration will **not** be possible.


Live migration modifications:
*****************************

Verify in _check_can_migrate_pci() whether the source instance contains
live migratable devices. If no live migratable devices are found, raise an
exception indicating that the migration is not possible.

.. note::
  The VM on the source host might have PCI devices attached that are not
  related to any PCI alias, but it is there because of neutron direct or
  direct-physical ports. In this case nova should do what it does today,
  detach these ports at the start of the migration and re-attach them on the
  dest after the migration. Also such PCI devices having no live_migratable=yes
  key in their extra_info should not prevent the live migration to be accepted.


Modify stats.py in the filter_pools() function to handle PCI requests for
live_migratable devices. Ensure it retrieves hosts with the appropriate number
of live migratable devices by adding a new filter.

Since VIF field is not used in this context, we need to claim PCI devices and
retrieve the PCI addresses of the destination host.

Update the ``LiveMigrateData`` object to include the PCI device mapping
between the source and destination device addresses. A new field,
``pci_dev_map_src_dst``, defined as a  ``DictOfStringsField`` will
be added to the ``LiveMigrateData`` object for this purpose.

Update the _live_migration_operation() function, with a specific
focus on the get_updated_guest_xml() function, to map the source PCI
addresses to the destination addresses in the destination XML file
using the data provided by the ``LiveMigrateData`` object.

.. note::
  - If PCI in Placement is enabled then live migration will work as today
    for neutron requested PCI devices (i.e. legacy behavior works)

  - If PCI in Placement is enabled then SR-IOV live migration proposed in
    this spec will still work (i.e. new functionality works)

  - Optionally PCI in Placement will be extended to automatically request
    HW_PCI_LIVE_MIGRATABLE trait if the alias has live_migratable="yes".

    - A further enhancement would be to extend the translation of the
      [pci]alias spec to placement RequestGroups to support forbidden traits.
      So when live_migratable=no is present in the alias the
      HW_PCI_LIVE_MIGRATABLE trait is requested as forbidden.

For NICs such as the Mellanox ConnectX-7, if both live_migrate=yes and
physical_network="label" are set, the migration mechanism defined in this
specification will be used instead of the legacy one.

However, this change will:

- Be implemented in a separate patch to allow the base case to land first.
- Ensure that such NICs are properly live migrated using the new code path.

.. __: https://github.com/openstack/nova/blob/f98f414f971b6c897bf48781a579730419b5a93d/nova/compute/pci_placement_translator.py#L597-L600

Alternatives
------------

NA


REST API impact
---------------

The `schema definition for PCI aliases`__ needs to be modified to allow the
specification of live migratable devices.

However, this change should not require a microversion bump.

.. __: https://github.com/openstack/nova/blob/b27447d55dbe6660eae7283ff7c32259d31967c7/nova/pci/request.py#L72-L117


Data model impact
-----------------

LiveMigrateDate object will be extended to supply the PCI devices info
of the destination host introducing a new ``pci_devices`` field.


Security impact
---------------

NA

Notifications impact
--------------------

NA


Other end user impact
---------------------

NA


Performance Impact
------------------

If PCI in placement is enabled, this `bug`__ should be taken into account
as it may impact performance.

`Mitigation measures`__ are currently being developed to minimize this impact.

.. __: https://bugs.launchpad.net/placement/+bug/2070257
.. __: https://review.opendev.org/q/topic:%22bug/2070257%22


Other deployer impact
---------------------

The user is fully responsible for configuring the following:

- Device specifications and aliases.
- Flavors: If users need to support multiple kinds of
  VFs, they must use different flavors for each VF type.


Developer impact
----------------

None

Upgrade impact
--------------

All VMs with devices that rely on the VFIO SR-IOV variant driver cannot
be migrated until they use a new flavor that includes the correct updated
aliases pointing to the revised PCI device specifications.

This can be achieved by resizing the VM and changing its flavor to the new one.

For NICs, an alternative approach could be to detach and reattach the device.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Uggla (René Ribaud)

Main contributors:
  Bauzas (Sylvain Bauza)

Feature Liaison
---------------

Feature liaison:
  N/A

Work Items
----------

- Parse live_migratable from [pci]dev_spec config.
- Add HW_PCI_LIVE_MIGRATABLE trait.
- Check source instance for appropriate live migratable devices.
- Add a new filter in filter_pools to manage live migratable devices.
- Update LiveMigrateData to include PCI device information.
- Update get_updated_guest_xml() function to include PCI device information.

Dependencies
============

- Support for devices using the variant driver interface.
  `specification`__.
- Performance impact bug.

.. __: https://specs.openstack.org/openstack/nova-specs/specs/2025.1/approved/enable-vfio-devices-with-kernel-variant-drivers.html

Testing
=======

- Unit tests and functional tests.
- Tempest and/or whitebox tests cannot be executed in CI due to hardware
  limitations. They can, however, be developed in parallel with this
  implementation and deferred for later inclusion in CI.

Documentation Impact
====================

Extensive admin and user documentation will be provided.

References
==========

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Epoxy
     - Introduced
