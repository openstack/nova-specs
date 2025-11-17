..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
libvirt: support cyborg owned MDEV in domain XML
================================================

https://blueprints.launchpad.net/nova/+spec/cyborg-vgpu-support

This blueprint proposes to enable generic vfio-mdev devices (MDEVs) managed
by Cyborg, such as vGPUs, in the Nova Libvirt driver.


Cyborg-managed MDEVs do not replace Nova's native vGPU or generic mdev
capabilities [1]_ and provide an alternative management mechanism in
parallel to the existing Nova feature.

Problem description
===================

To allow operators to use Cyborg for vGPU lifecycle management, or any other
externally managed vfio-mdev devices, Cyborg must discover the MDEVs,
report them to Placement, and instruct Nova to allocate a specific vfio-mdev
to the instance in response to an Accelerator Request (ARQ).

The current Cyborg-Nova interaction [2]_ lacks Libvirt driver support
for ARQ bindings of type MDEV. This spec addresses this gap by enabling
the Libvirt driver to compose Cyborg-owned MDEVs into the domain XML.

Use Cases
---------

As an operator, I want to use Cyborg to manage the lifecycle of generic
vfio mediated devices (e.g. vGPUs).

Proposed change
===============

This spec proposes to complete the support for Cyborg managed MDEVs in Nova.
In the Wallaby release, we have completed the support for Cyborg managed vGPUs
in Cyborg, however, the Nova libvirt driver still does not support composing
Cyborg owned MDEV into domain XML.

Cyborg managed MDEVs follow the same Nova-Cyborg interaction introduced in
ussuri [2]_. In short, the pre-existing (and not changed in this spec)
interaction flow is the following:

1. Operator creates a device profile in Cyborg for the GPU and a Nova flavor
   referencing it (``accel:device_profile=...``)
2. Cyborg discovers the configured devices and reports inventory to Placement
   with the ``OWNER_CYBORG`` trait
3. User requests an instance with the Cyborg-aware flavor
4. Nova scheduler queries Placement, which selects a host with matching
   inventory and traits
5. Cyborg binds the ARQ and returns an ``attach_handle`` with the
   corresponding type, a UUID, and ``attach_handle_info`` containing the
   parent PCI address and possibly other fields (see below for a description
   of those fields in an ARQ of ``MDEV`` type)
6. For an ARQ of ``MDEV`` type, Nova compute (libvirt) calls
   ``_create_mdev`` with the parent device and mdev type from
   ``attach_handle_info`` and the UUID from ``attach_handle_uuid``, creating
   a persistent mdev with the correct vGPU type in a single operation
7. Nova composes the domain XML including the mdev reference and boots the VM
8. On instance delete, Nova/libvirt removes the mdev and Cyborg reconciles
   its ARQ state

Cyborg defines a data model in ARQ to track a Cyborg owned MDEV.
This data model provides ``attach_handle_type`` to distinguish from a
PCI device accelerator, and ``attach_handle_uuid`` as the mdev UUID which is
used to populate the xml with a reference to the pre-created mdev.

The ``attach_handle_info`` field of the ``attach_handle`` returned by Cyborg
contains the same fields used in a PCI one (``domain``, ``bus``, ``device``
and ``function``), plus an additional ``asked_type`` which describes the mdev
type. The format is as follows:

::

    {
        'attach_handle_type': 'MDEV',
        'attach_handle_uuid': '91ac1606-427e-44bb-8233-f4ff4bf3d241',
        'attach_handle_info': {
            'asked_type': 'mtty',
            "domain": "0000",
            "bus": "10",
            "device": "1",
            "function": "0",
        },
    }

The libvirt driver will be extended to render the appropriate xml
for the given mdev.

This involves getting mdevs from the ARQ list and passing them to generate
guest XML by extending the ``_get_guest_config`` method
in ``nova/virt/libvirt/driver.py``.

.. code-block:: python

    def _get_guest_config(self, instance, network_info, image_meta,
                          disk_info, rescue=None, block_device_info=None,
                          context=None, mdevs=None, accel_info=None,
                          share_info=None):
      ...
      if accel_info:
        # NOTE(Sundar): We handle only the case where all attach handles
        # are of type 'PCI'. The Cyborg fake driver used for testing
        # returns attach handles of type 'TEST_PCI' and so its ARQs will
        # not get composed into the VM's domain XML. For now, we do not
        # expect a mixture of different attach handles for the same
        # instance; but that case also gets ignored by this logic.
        mdev_arq_list = []
        pci_arq_list = []
        unsupported_types = set()

        for arq in accel_info:
            match arq['attach_handle_type']:
                case 'MDEV':
                    mdev_arq_list.append(arq)
                case 'PCI':
                    pci_arq_list.append(arq)
                case _:
                    unsupported_types.add(other_type)

        if unsupported_types:
            LOG.info('Ignoring accelerator requests for instance %s. '
                     'Supported Attach handle types: PCI, MDEV. '
                     'But got these unsupported types: %s.',
                     instance.uuid, unsupported_types)

        if mdev_arq_list:
            self._guest_add_mdevs(guest, mdev_arq_list)
        if pci_arq_list:
            self._guest_add_accel_pci_devices(guest, pci_arq_list)
        ...

.. note::

  Nova will use the ``_create_mdev`` method and the libvirt support for
  persistent mdevs introduced in I7e1d10e66a260efd0a3f2d6522aeb246c7582178.

  https://github.com/openstack/cyborg/commit/79e1928554b6a03dd481ebefd3f550adeb457aed
  added the parent device and mdev type information to the ARQ bindings.
  Nova will use this information to create a persistent mdev.


To prevent collisions between Nova and Cyborg managed mdevs, we will complete
the remaining work of the ``owner-nova-trait-usage`` spec
[3]_. This entails:

* Tagging every ResourceProvider that Nova creates with a ``OWNER_NOVA`` trait.
* Adding a new compute service version for this functionality.
* Providing a pre-filter that will add the trait for every Nova request group.

The pre-filter will only be enabled if the minimum compute service version is
higher than the new compute service version for this feature. This check in
the pre-filter will mitigate any upgrade impact and avoid the need for config
options.

An allocation reshape is not required as we are only updating the resource
provider traits, not the allocations.

Additionally, we will add a check while composing the xml to ensure the device
being used is not also configured to be used by Nova. In such a case, we will
log a warning to inform the operator that the device is misconfigured and it
should be used exclusively by Nova or Cyborg, but that it can't be used by both
services.

As a result of this spec, there will be no change in the operations on
instances with attached accelerator resources supported, which are described in
the Cyborg documentation [4]_.

Alternatives
------------

Manage all devices in Nova.
If we do not complete this work, the operator will have to continue
to use Nova for vGPU/mdev device management.
If we decide not to extend Nova to integrate more with Cyborg, we
should instead reverse course and remove all Cyborg support and pull
all device management use cases back into Nova.

We considered not using ``_create_mdev`` or the libvirt support for persistent
mdevs. In that model, Cyborg and the installer would be responsible for
ensuring the persistence of the host mdev across reboots with a stable UUID.
This was not pursued to reduce the parity gap between the Nova and Cyborg mdev
management.

Data model impact
-----------------

None

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

None

Other deployer impact
---------------------

Ensure devices are managed by only one service.

If the deployer configures the same device in both Cyborg and Nova,
they may report the same data to Placement simultaneously, causing
scheduling conflicts or incorrect device sharing.

While Nova-managed vGPUs and Cyborg-managed vGPUs can coexist on the
same host, avoid this configuration to minimize the risk of accidental
device sharing.

Developer impact
----------------

None

Upgrade impact
--------------

None, existing workloads should not be affected by the changes proposed here.

A new compute service version will be introduced to advertise
support for reporting the Nova owner trait. A scheduler pre-filter
will be added to include the Nova owner trait only when the min
compute service version is greater than the new compute service version.

To migrate from a Nova-owned vGPU to a Cyborg-owned vGPU, create a
snapshot of the instance, delete it, and boot a new instance from the
snapshot using a flavor with a Cyborg-managed MDEV
(accel:device-profile=cyborg-vgpu-device-profile-name). Note that this
is a delete-and-recreate, not a seamless migration: the instance UUID
will change, network ports are detached unless pre-created, ephemeral
storage is lost, and GPU state (VRAM, contexts) is not preserved.

This generally requires extra capacity to support the Cyborg-owned vGPUs
as a single host device cannot be shared between Nova and Cyborg.

The Nova generic mdev support is still fully supported and no changes
should be required to existing users of the Nova generic mdev support.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jgilaber

Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  None

Work Items
----------

* Complete the libvirt driver support for ARQ bindings of type MDEV.

* Add OWNER_NOVA trait to Nova managed resource providers.

Dependencies
============

End to end testing of the new functionality will require some Cyborg driver
that creates attach handles of type ``MDEV``. One such driver is
currently being proposed [5]_.

Testing
=======

Unit and functional tests will be added to test the XML generation.
The Cyborg job will be extended to create mdevs and bind ARQs using
the mtty/mdpy kernel modules.

As part of this work, a new generic mdev driver will be created for
Cyborg to support the mtty/mdpy devices or any other generic mdev
devices [5]_.

As a stretch goal, we will also complete the remaining work to support
mtty/mdpy devices in Nova native generic mdev support to enhance
testing of the shared mdev functionality.
https://review.opendev.org/q/topic:%22mtty_support%22

Documentation Impact
====================

Documentation will be enhanced to include creating a flavor with a
Cyborg-owned vGPU and note limitations of using Cyborg-owned vGPUs
such as no live migration support. This will follow the same pattern
as the Nova-owned vGPU documentation
https://docs.openstack.org/nova/latest/admin/virtual-gpu.html#caveats
but will be created as a new document in the Nova admin
documentation.

References
==========

.. [1] https://docs.openstack.org/nova/ussuri/admin/virtual-gpu.html
.. [2] https://specs.openstack.org/openstack/nova-specs/specs/ussuri/implemented/nova-cyborg-interaction.html
.. [3] https://specs.openstack.org/openstack/nova-specs/specs/zed/approved/owner-nova-trait-usage.html
.. [4] https://docs.openstack.org/cyborg/latest/reference/support-matrix.html
.. [5] https://review.opendev.org/c/openstack/cyborg-specs/+/982276

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
   * - 2026.1
     - Reproposed
   * - 2026.2
     - Reproposed
