..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Libvirt: support vDPA based networking
======================================

https://blueprints.launchpad.net/nova/+spec/libvirt-vdpa-support

Over the years a number of different technologies have been developed to
offload networking and other function to external processes in order to
accelerate QEMU instance performance. In kernel 5.7+ a new virtual bus know as
*vDPA* (vHost data path acceleration) was introduced to provide a vendor
neutral way to accelerate standard virtio device using software or hardware
accelerator implementations. vDPA support was introduced in Libvirt 6.9.0 to
leverage the vDPA capabilities introduced in QEMU 5.1+.
This blueprint tracks enhancing nova to leverage these new capabilities
for offloading to hardware-based smart NICs via hardware offloaded OVS.

Problem description
===================

Current hardware offloaded networking solutions require vendor specific drivers
in the guest to function. The vDPA bus allows an abstraction layer to exist
between the accelerator and the VM without the CPU overhead of traditional
software vHost implementations. vDPA-enabled vSwitch offloads allow
the guest to use standard virtio drivers instead of a vendor specific driver.

.. note::

   While vDPA is expected to support live migration in the future, QEMU does
   not currently support live migration with vDPA devices. One of the main
   advantages of vDPA based networking over SR-IOV is the ability to abstract
   the device state from the VM, allowing transparent live migration via a
   software fallback. Until that fallback is implemented in QEMU, live
   migration will be blocked at the API layer via a HTTP 409 (Conflict) error
   response so that we can enable it without a new micro-version.

   As Open vSwitch is currently the only control plane capable of managing vDPA
   devices, and since that requires hardware offloads to function, this spec
   will focus on enabling vDPA networking exclusively with hardware-offloaded
   OVS. In a future release this functionality can be extended to other vSwitch
   implementations such as VPP or linux bridge if they become vDPA enabled.

Use Cases
---------

As an operator, I want to offer hardware-accelerated networking without
requiring tenants to install vendor-specific drivers in their guests.

As an operator, I want to leverage hardware-accelerated networking while
maintaining the ability to have transparent live migration.

.. note::

   Transparent live migration will not initially be supported and will be
   enabled only after it is supported officially in a future QEMU release.

Proposed change
===============

* A new vnic-type ``vdpa`` has been introduced to neutron to request vDPA
  offloaded networking. https://github.com/openstack/neutron-lib/commit/8c6ab5e
* The ``nova.network.model`` class will be extended to define the new ``vdpa``
  vnic-type constant.
* The libvirt driver will be extended to generate the vDPA interface XML
* The PCI tracker will be extended with a new device-type, ``VDPA``.
  While the existing whitelist mechanism is unchanged, if a device is
  whitelisted and is bound to a vDPA driver, it will be inventoried as
  ``VDPA``. In the libvirt driver this will be done by extending the private
  ``_get_pci_passthrough_devices`` and ``_get_device_type`` functions to detect
  if a VF is a parent of a vDPA nodedev. These functions are called by
  ``get_available_resources`` in the resource tracker to generate the
  resources dictionary consumed by  ``_setup_pci_tracker`` at the startup of
  the compute agent in ``_init_compute_node``.

.. note::

   The vDPA device type is required to ensure that the VF associated with vDPA
   devices cannot be allocated to VMs via PCI alias or standard neutron SR-IOV
   support. VFs associated with vDPA devices cannot be managed using standard
   kernel control plane command such as ``ip``. As a result, allocating them
   to an interface managed by the ``sriov-nic-agent`` or via alias-based PCI
   passthrough is not valid. This will also provide automatic NUMA affinity
   and a path to eventurally report vDPA devices in placement as part of
   generic PCI device tracking in placement in the future.


Alternatives
------------

We could delegate vDPA support to cyborg.
This would still require the libvirt changes and neutron changes while
also complicating the deployment. Since vDPA-based NICs are fixed function
NICs there is not really any advantage to this approach that justifies
the added complexity of inter-service interaction.

We could use the resources table added for vPMEM devices to track the devices
in the DB instead of the PCI tracker. This would complicate the code paths as
we would not be able to share any of the PCI NUMA affinity code that already
exists.

We could support live migration by treating vDPA devices as if they are
direct mode SR-IOV interface, meaning nova would hot unplug and plug
the interface during the migration. In the future this could be replaced with
transparent live migration if the QEMU version on both hosts is new enough.
Since we don't know when that will be, this option is deferred until a future
release to reduce complexity.

A new workaround config option could be added
``enable_virtual_vdpa_devices=True|False`` (default: ``False``). When set to
``True`` it would allow a virtual vDPA devices such as the ``vdpa_sim``
devices to be tracked and used. Virtual PCI devices do not have a VF or PCI
device associated with them, so setting this value would result in the no-op
os-vif driver being used and a sentinel value being used to track the device
in the PCI tracker. This would allow testing without real vDPA hardware in CI
and is not intended for production use. This was declared out of scope to
avoid adding a config option and code that is purely used for testing.
Functional tests will be used instead to ensure adequate code coverage.

A new standard trait ``HW_NIC_VDPA``  could be reported by the
libvirt driver on hosts with vDPA devices, and the required version of QEMU
and libvirt. This would be used in combination with a new placement prefilter
to append a required trait request to the unnamed group if any VM interface has
vnic-type ``vdpa``. This will not be done as it will not be required when
PCI devices are tracked in placement. Since standard traits cannot be removed,
no new trait will be added and the PCI passthrough filter will instead be used
to filter host on device type.

Data model impact
-----------------

The allowed values of the vnic-type in the ``nova.network.model.VIF`` class
will be extended. The allowed values of the ``device_type`` column in the
``pci_devices`` table will be extended.

Optionally, the ``VIFMigrateData`` or ``LibvirtLiveMigrateData`` object can be
extended to denote the destination host support transparent vDPA live
migration. This is optional as currently it would always be false until a QEMU
and libvirt version are released that support this feature.

REST API impact
---------------

The neutron port-binding extension vnic-types has been extended
to add vnic-type ``vdpa``. No nova API changes are required.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

vDPA ports will work like SR-IOV ports from an end user perspective,
however the device model presented to the guest will be a virtio NIC
and live migration will initially be blocked until supported by QEMU.

Performance Impact
------------------

The performance will be the same as SR-IOV
in terms of dataplane performance and nova scheduling or VM creation
a.k.a. None.

Other deployer impact
---------------------

vDPA requires a very new kernel and very new versions of QEMU and libvirt to
use.  Initial support for vDPA was added in kernel 5.7, QEMU 5.1 and
libvirt 6.9.0.

The operator will need to ensure all dependencies are present to use
this feature. Intel NIC support is present in 5.7 at the time of writing,
no NIC that support vDPA is available on the market from Intel.
The first publicly available NICs with vDPA capabilities are the
Mellanox/Nvidia ConnectX-6 DX/LX NICs, which are only enabled in kernel 5.9

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
  sean-k-mooney

Other contributors:
  stephen.finucane

Feature Liaison
---------------

sean-k-mooney

Work Items
----------

- Update libvirt driver
- Add prefilter
- Add docs
- Update tests

Dependencies
============

- libvirt 6.9.0+
- QEMU 5.1+
- Linux 5.7+

Testing
=======

This will be tested primarily via unit and functional tests,
however a Tempest job using the vDPA sim module may be created
if it proves practical to do so. The main challenges to this are
creating a stable testing environment with the required dependencies.
Fedora rawhide has all the required dependencies but ships with python 3.9.
OpenStack currently does not work properly under python 3.9

Alternative test environments such as Ubuntu 20.04 do not provide new enough
kernel by default or do not ship the required libvirt and QEMU versions.
Compilation from source is an option but we may or may not want to do that in
the upstream CI.

Documentation Impact
====================

The existing admin networking document will be extended to introduce vDPA
and describe the requirement for use.

References
==========

The nova-neutron PTG discussion on this topic can be found on line 186
here: https://etherpad.opendev.org/p/r.321f34cf3eb9caa9d87a9ec8349c3d29

An introduction to this topic and is available as a blog at
https://www.redhat.com/en/blog/introduction-vdpa-kernel-framework
and other blogs on the topic covering the evolution and current state
are also available https://www.redhat.com/en/blog?search=vdpa

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
   * - Wallaby
     - Updated to reflect changes to HTTP error codes
