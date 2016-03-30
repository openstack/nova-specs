
..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Boot From UEFI image
==========================================

https://blueprints.launchpad.net/nova/+spec/boot-from-uefi

The nova compute libvirt driver does not support booting from UEFI images.
This is a problem because there is a slow but steady trend for OSes to move
to the UEFI format and in some cases to make the UEFI format their only
format. Microsoft Windows is moving in this direction and Clear Linux is
already in this category. Given this, we propose enabling UEFI boot with
the libvirt driver. Additionally, we propose using the well tested and
battle hardened Open Virtual Machine Firmware (OVMF) as the VM firmware
for x86_64.

Unified Extensible Firmware Interface (UEFI) is a standard firmware designed
to replace BIOS. Booting a VM using UEFI/OVMF is supported by libvirt since
version 1.2.9.

OVMF is a port of Intel's tianocore firmware to qemu virtual machine, in other
words this project enables UEFI support for Virtual Machines.

Problem description
===================
Platform vendors have been increasingly adopting UEFI for the platform firmware
over traditional BIOS. This, in part, is leading to OS vendors also shifting to
support or provide UEFI images. However, as adoption of UEFI for OS images
increases, it has become apparent that OpenStack through its Nova compute
Libvirt driver, does not support UEFI image boot. This is problematic and needs
to be resolved.

Use Cases
----------
1. User wants to launch a VM with UEFI. In this case the user needs to be able
to tell Nova everything that is needed to launch the desired VM. The only
additional information that should be required is new image properties
indicating which kind of firmware type will be used, uefi or bios.

Proposed change
===============

Add missing elements when generating XML definition in libvirt driver to
support OVMF firmware. Add also a new image metadata value to specify which
firmware type will be used.

The following is the new metadata value.

* 'hw_firmware_type': fields.EnumField()

This indicates that which kind of firmware type will be used to boot VM.
This property can be set to 'uefi' or 'bios'. 'uefi' will indicate that
uefi firmware will be used. If the property is not set, 'bios' firmware
will be used.

Alternatives
------------

None

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

The following packages should be added to the system:

    * ovmf

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
qiaowei-ren

Other contributors:
Victor Morales <victor.morales@intel.com>
Xin Xiaohui <xiaohui.xin@intel.com>


Work Items
----------

The primary work items are

* Add the 'hw_firmware_type' field to the ImageMetaProps object
* Update the libvirt guest XML configuration when the UEFI image
  property is present

Dependencies
============

This spec only implements uefi boot for x86_64 and arm64. And this
spec will depend on the following libraries:

* libvirt >= 1.2.9
* OVMF from EDK2

Testing
=======

Would need new unit tests. Without some kind of functional testing,
there is a warning emitted when this is used saying it's untested
and therefore considered experimental.

Documentation Impact
====================

Some minor additions for launching a UEFI image with Nova, note on
extra config option and metadata property, Operator / installation
information for the UEFI firmware. In addition, hypervisor support
matrix should be also updated.

References
==========

* http://www.linux-kvm.org/downloads/lersek/ovmf-whitepaper-c770f8c.txt

* https://libvirt.org/formatdomain.html#elementsOSBIOS

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
