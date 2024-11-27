..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================================================
Enable VFIO devices with kernel variant drivers
=============================================================================

https://blueprints.launchpad.net/nova/+spec/enable-vfio-devices-with-kernel-variant-drivers

This spec outlines the necessary steps to enable support for SR-IOV devices
using the new kernel VFIO SR-IOV variant driver interface.

Problem description
===================

Starting with kernel 5.16 and continuing in subsequent kernels, including
those in Ubuntu 24.04 (Noble Numbat) and future RHEL 10 releases, the SR-IOV
mechanism for sharing Virtual Functions (VFs) with a guest has evolved.

While the older interfaces are still supported, a new interface using
`variant drivers`__ has been introduced. Several devices already leverage
this newer variant driver interface.

As a result, Nova should update its VFIO device support to accommodate
this advancement.

.. __: https://docs.kernel.org/driver-api/vfio-pci-device-specific-driver-acceptance.html

Use Cases
---------

- As an operator, I want to use SR-IOV devices on Linux distributions that
  require variant drivers.

- As an operator, I want "legacy" SR-IOV devices support to remain compatible.

Proposed change
===============

Description:
------------

SR-IOV devices using the variant driver interface can likely be integrated
with Nova by building upon the existing PCI passthrough and SR-IOV support,
combined with several modifications proposed in this specification.

According to the device documentation, users should configure the devices
to be accessible as PCI Virtual Functions (VFs) identified by their PCI
addresses.

Subsequently, by following the `Nova documentation on attaching physical PCI
devices to guests`__, users should arrive at a main configuration PCI section
that specifies device attributes and aliases.


Configuring managed mode:
*************************

Users must specify whether the PCI device is managed by libvirt to allow
detachment from the host and assignment to the guest, or vice versa.
The managed mode of a device depends on the specific device and the support
provided by its driver.

The proposed solution is to add a ``managed`` tag to the device
specification.

- ``managed='yes'`` means that nova will let libvirt to detach the device
  from the host before attaching it to the guest and re-attach it to the host
  after the guest is deleted.
- ``managed='no'`` means that nova will not request libvirt to detach / attach
  the device from / to the host. In this case nova assumes that the operator
  configured the host in a way that these VFs are not attached to the host.

.. note::

  If not set, the default value is managed='yes' to preserve the existing
  behavior, primarily for upgrade purposes.

  The behavior, specifically for Nova, assumes that the devices are already
  bound to vfio-pci or the relevant variant driver and are directly usable
  without any additional operations to enable passthrough to QEMU.


.. warning::

  Incorrect configuration of this parameter may result in host OS crashes.

When this tag is encountered by the `PCI resource tracker`__, the
corresponding information will be stored in the respective PciDevice
object under the extra_info field.
This allows the code responsible for generating the XML definition to
configure the libvirt-managed mode with the appropriate value.

.. note::

  The PciDevice object version remains unchanged.


Sanitize device specification:
******************************

As part of the initialization process, checks are performed to validate
the correctness of the device specifications. Currently, if duplicates are
present in the specifications, only the first entry is retained. While this
behavior is acceptable, we may consider extending it in the future to log
a warning and notify the user.

Display management:
*******************

From libvirt documentation:

  An optional display attribute may be used to enable using a vgpu device
  as a display device for the guest. Supported values are either on or off
  (default). There is also an optional ramfb attribute with values of either
  on or off (default). When enabled, the ramfb attribute provides a memory
  framebuffer device to the guest. This framebuffer allows the vgpu to be used
  as a boot display before the gpu driver is loaded within the guest. ramfb
  requires the display attribute to be set to on.

There is a constraint to activate these settings for only one VGPU, even
if multiple VGUs are attached to a VM.

.. note::

  In this initial implementation, display management is out of scope,
  consistent with the existing mdev implementation.

Examples:

.. note::

  The following example demonstrates device specifications and alias
  configurations.

.. code-block:: shell

  [pci]
  device_spec = { "vendor_id": "10de", "product_id": "25b6", "address": "0000:25:00.4", managed: "no" }

  alias = { "vendor_id": "10de", "product_id": "25b6", "device_type": "type-VF", "name": "MYVF" }

Creating a VM based on the configuration above will include the following
snippet in the XML definition:

.. code-block:: shell

  <hostdev mode='subsystem' type='pci' managed='no'>
    <driver name='vfio'/>
    <source>
      <address domain='0x0000' bus='0x25' slot='0x00' function='0x4'/>
    </source>
    <alias name='hostdev0'/>
    <address type='pci' domain='0x0000' bus='0x00' slot='0x05' function='0x0'/>
  </hostdev>


The above example does not apply if users need to support multiple kinds
of VFs.


Support for multiple kinds of VFs:
**********************************

SR-IOV devices, such as GPUs, can be configured to provide VFs with various
characteristics under the same vendor ID and product ID.

To enable Nova to model this, if you configure the VFs with different
resource allocations, you will need to use separate resource_classes for each.

This can be achieved by following the steps below:

- Enable PCI in Placement: This is necessary to track PCI devices with
  custom resource classes in the placement service.
- Define Device Specifications: Use a custom resource class to represent
  a specific VF type and ensure that the VFs existing on the hypervisor are
  matched via the VF's PCI address.
- Specify Type-Specific Flavors: Define flavors with an alias that matches
  the vendor, product, and resource class to ensure proper allocation.


Device specification resource class:
************************************

This is necessary for users who want to support multiple kinds of VFs,
requiring the "PCI in placement" feature to be enabled.

The resource class can user defined provided it conforms to the placement,
validation requirements.
While nova will normalize the resource class string to produce a valid
resource class, relying on this is considered bad practice.

Normalisation is done by making the string upper case, replacing any
consecutive character outside of `[A-Z0-9_]`  with a single ‘_’, and
prefixing the name with `CUSTOM_` if not yet prefixed.

For example, ``CUSTOM_<TYPE_OF_VF>`` i.e. ``CUSTOM_GOLD_GPU`` would be a
valid resource class.


Examples:

.. note::

  The following example demonstrates device specifications and alias
  configurations, utilizing resource classes as part of the "PCI in
  placement" feature.

.. code-block:: shell

  [pci]
  device_spec = { "vendor_id": "10de", "product_id": "25b6", "address": "0000:25:00.4", "resource_class": "CUSTOM_A16_16A", "managed": "no" }

  alias = { "device_type": "type-VF", resource_class: "CUSTOM_A16_16A", "name": "A16_16A" }


.. __: https://docs.openstack.org/nova/latest/admin/pci-passthrough.html
.. __: https://github.com/openstack/nova/blob/f98f414f971b6c897bf48781a579730419b5a93d/nova/compute/pci_placement_translator.py#L597-L600


Alternatives
------------

NA


REST API impact
---------------

NA

Data model impact
-----------------

Only the existing extra_info free dict will be extended.

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

- Host device: Define the kinds of virtual VFs required.
- Compute Node: Configure device specifications, including whether the
  device/driver supports managed=true, along with the necessary aliases.
- Flavors:  If multiple kinds of VFs are needed, users must create and use
  different flavors for each VF type.

Developer impact
----------------

None

Upgrade impact
--------------

Users with Nvidia virtual GPUs must review their configuration.

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

- Parse managed parameter from PCI device specification.
- Sanitize device specification.
- Change XML generation to deal with managed parameter.
- Documentation updates.
- Unit tests + functional tests.

Dependencies
============

- Performance impact bug.
- PCI in placement features for multiple kinds of VFs.


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
