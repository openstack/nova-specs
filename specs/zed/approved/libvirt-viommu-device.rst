..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Add Virtual IOMMU device support for libvirt driver
===================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-viommu-device

The spec adds support to expose a virtual IO memory mapping unit (vIOMMU) with
libvirt driver.

Problem description
===================

Currently it is possible to use libvirt to expose vIOMMU to a guest when using
the x86 Q35 or ARM virt machine types. On some platfroms such as AArch64 an
vIOMMU is required to fully support PCI passthough and in general it can enable
use of vfio-pci in guests that require it. Nova does not currently expose
vIOMMU functionality to operators or users.

Use Cases
---------

* As an operator deploying nova on aarch64, I would like to be able to leverage
  PCI passthrough to support assigning accelerators and other PCIe devices to
  my guests.

* As an operator, I would like to enable my end users to use dpdk in their vms

* As a vnf vendor, that delivers applications that leverage accelerators that
  require an iommu I would like to express that as an attribute of the image.

* As an operator, I would like to nova to expose vIOMMU capability on a host
  that supports it and automatically place vms that requires it on appropriate
  hosts.

Proposed change
===============

* This spec proposes adding new guest configs for
  IOMMU (``LibvirtConfigGuestIOMMU``) and
  APIC feature (``LibvirtConfigGuestFeatureIOAPIC``).

* Add following attribute to image property and extra_specs:

  * ``hw_viommu_model`` (for image property) and
    ``hw:viommu_model`` (for extra_specs):
    Support values none|intel|smmuv3|virtio|auto. Default to ``none``.
    ``auto`` will select ``virtio`` if Libvirt supports it,
    else ``intel`` on X86 and ``smmuv3`` on AArch64.

  above attribute is on of options for ``LibvirtConfigGuestIOMMU``, More
  information for them can be found in `libvirt format domain`_.

* Add IOMMU config when generating guest config. And enable IOAPIC within.

* Add ``hw_locked_memory`` for image property and ``hw:locked_memory`` for
  extra specs. This will make sure ``locked`` element is present in the
  ``memoryBacking``, but only allow it if you have also set
  ``hw:mem_page_size``, so we can ensure that the scheduler can actually
  account for this correctly and prevent out of memory events.
  Here is a reference to related issue `MEMLOCK_RLIMIT`_.
  Locked memory not only disables memory over subscription but it also prevent
  the kernel form swapping the memory.
  Enable this will disable the RLIMITs for the VM in cases where you have a
  large number of passed through devices.
  When assigning multiple devices to the same VM. The issue is that with a
  guest IOMMU, each assigned device has a separate address space that is
  initially configured to map the full address space of the VM and each
  vfio container for each device is accounted separately. Libvirt will only
  set the locked memory limit to a value sufficient for locking the memory
  once, whereas in this configuration we're locking it once per assigned
  device. Without a guest IOMMU, all devices run in the same address space
  and therefore the same container, and we only account the memory once for
  any number of devices (with  ``hw:mem_page_size`` set to any value this will
  enable the NUMA toplogy fitler to schdule based on the fact the memory can't
  be over commited).

* For ``aw_bits`` attribute in ``LibvirtConfigGuestIOMMU``:
  This attribute can used to set the address width to allow mapping larger iova
  addresses in the guest. Since 6.5.0 (QEMU/KVM only).
  As Qemu current supported values are 39 and 48, I propose we set this to
  larger width (48) by default and will not exposed to end user.

* For ``eim`` attribute in ``LibvirtConfigGuestIOMMU``:
  this will not exposed to end user, but will directly enabled if machine type
  is Q35.
  Side Note:
  eim(Extended Interrupt Mode) attribute (with possible values on and off)
  can be used to configure Extended Interrupt Mode.
  A q35 domain with split I/O APIC (as described in hypervisor features),
  and both interrupt remapping and EIM turned on for the IOMMU, will be
  able to use more than 255 vCPUs. Since 3.4.0 (QEMU/KVM only).

* Provide iommu model trait for each viommu model.

* Add ``hw_viommu_model`` to request_filter, this will extend the
  transform_image_metadata prefilter to select host with the correct model.

* Provide new compute ``COMPUTE_IOMMU_MODEL_*`` capablity trait for each model
  it supports in driver.

.. _`libvirt format domain`: https://libvirt.org/formatdomain.html#iommu-devices
.. _`SEV`: https://blueprints.launchpad.net/nova/+spec/amd-sev-libvirt-support
.. _`MEMLOCK_RLIMIT`: https://listman.redhat.com/archives/vfio-users/2018-July/msg00001.html

Alternatives
------------

None

Data model impact
-----------------

None.

REST API impact
---------------

None

Security impact
---------------

None.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

Enable vIOMMU might introduce significant performance overhead.
You can see performance comparision table from
`AMD vIOMMU session on KVM Forum 2021`_.
For above reason, vIOMMU should only be enable for workflow that require it.

.. _`AMD vIOMMU session on KVM Forum 2021`: https://static.sched.com/hosted_files/kvmforum2021/da/vIOMMU%20KVM%20Forum%202021%20-%20v4.pdf

Other deployer impact
---------------------

Operators will see new extra spec options and image properties.

Developer impact
----------------

None

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  stephenfin

Other contributors:
  ricolin

Feature Liaison
---------------

Feature liaison:
  None

Work Items
----------

* Add new guest configs: https://review.opendev.org/c/openstack/nova/+/830646

* Add docs for new guest options in extra_specs and image properties.

Dependencies
============

None

Testing
=======

* Unit test for in patch.
* We can work on more advance test against real environment.
  Not that needed for this patch IMO but we still should provide certain level
  of examine for extra guarantee.

Documentation Impact
====================


* New docs for new guest options in extra_specs and image properties
  documentation.

References
==========

* patch: https://review.opendev.org/c/openstack/nova/+/830646
* AMD vIOMMU session on KVM Forum 2021: https://static.sched.com/hosted_files/kvmforum2021/da/vIOMMU%20KVM%20Forum%202021%20-%20v4.pdf
