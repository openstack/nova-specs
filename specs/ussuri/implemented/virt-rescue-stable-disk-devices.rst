..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
Virtual instance rescue with stable disk devices
================================================

https://blueprints.launchpad.net/nova/+spec/virt-rescue-stable-disk-devices

This will provide the ability to indicate that the rescue disk image
should be attached as a transient disk device (ie USB stick), so that
existing storage attached to an instance doesn't change its device
address during rescue mode.

Problem description
===================

When an instance is booted normally there are a number of possible disks
that will be attached to the instance

- An ephemeral or persistent cinder volume root disk
- Zero or more ephemeral non-root disks
- Zero or more persistent non-root cinder volumes
- An optional swap disk
- An optional config drive disk

When the instance is booted in rescue mode though, this storage setup
changes significantly, and differently depending on virt drivers. In
the Libvirt driver, the rescue instance gets:

- A rescue root disk
- The original root disk
- An optional config drive disk

There are multiple problems with this. First of all several of the disks
are missing entirely, eg the ephemeral non-root disks, all cinder volumes
and the swap disk. This missing storage limits the scope of work the admin
can do in rescue mode.

The rescue root disk is put on a device that previously held the real
root disk. For example the rescue root is /dev/vda and the real root image is
now shifted to a different device /dev/vdb. Although a well designed
OS setup should not rely on the root device appearing at a fixed device
name, some OSes none the less do depend on this. Moving the root disk
during rescue mode can thus introduce problems of its own, and in fact
contribute to mistakes in rescue mode. For example it may confuse the admin
into setting up their fstab to refer to /dev/vdb, when the root disk will go
back to /dev/vda after rescue mode is finished.

This change in disk presence during rescue mode is very different to
what happens to disks on a baremetal machine when booted from rescue
media. This means that admin knowledge from working in a bare metal
world needs to be re-learned for OpenStack rescue mode, which adds an
undesirable learning burden for the admin.

When disks change what address they appear at, this can cause upset
licensing checks of some guests OS too. For example, if hardware
devices change their address too frequently, Windows may decide to
ask for license re-activation. This is again an undesirable thing
for admins in general.

Use Cases
----------

When the tenant user boots a VM in rescue mode they expect the existing
storage device configuration to be identical to that seen when running
in normal mode, but with an extra transient disk hotplugged to represent
the rescue media.

Proposed change
===============

This spec will not cover the removal of the current boot from volume check in
the compute API that currently blocks any attempt to rescue an instance using a
root cinder volume. The removal of this check and subsequent impact on the
overall API will be covered in a follow up spec.

The compute manager code will be changed such that when rescue is performed the
full block device mapping will be present. This will allow instances to be
configured with the full set of non-root cinder volumes that would appear
during normal boot.

New image properties have already been introduced during Ocata [1]_ that will
be used to indicate the type of device and associated bus to use as the rescue
device.

- hw_rescue_bus=virtio|ide|usb|scsi
- hw_rescue_device=disk|floppy|cdrom

If omitted, the virt driver will default to whatever behaviour it currently
has for setting up the rescue disk. For the Libvirt driver, this means the
default bus would match the hw_disk_bus, and the device type would be "disk".

The expected recommended setup would be to tag the rescue image in glance
with hw_rescue_bus=usb, which would indicate to the virt driver that it
should attach a USB flash drive to the guest, containing the rescue image.
For hypervisors which can't support this an alternative recommendation would
be to tag the rescue image with hw_rescue_bus=ide and hw_rescue_device=cdrom
to cause a new CDROM device to be exposed with the rescue media.

The Libvirt nova driver will be changed so that when booting in rescue mode,
all the non-root cinder volumes, local ephemeral non-root disks and swap disks
are present in rescue mode. The rescue root device will be added as the *last*
device in the configuration, but will be marked as bootable for the BIOS, so it
takes priority over the existing root device. This relies on KVM/QEMU
supporting the "bootindex" parameter, which all supported versions do. This new
rescue mode would not be supported by Xen, nor LXC.

Other virt driver maintainers may wish to also implement this blueprint, so
approval should be considered to give blessing to all virt drivers. If other
virt driver maintainers wish to commit to doing this in this cycle the list
of assignees will be updated.

Alternatives
------------

Do nothing is always an option, but the current setup has a number of
undesirable characteristics described earlier.

An alternative might be to simply hardcode a different approach. eg when
using KVM simply always use a USB flash device as the rescue media, and
don't bother with supporting an image property. This is certainly a viable
option, and if it were not for the sake of maintaining backwards compatibility
with earlier OpenStack, it might even be the preferred approach.

Data model impact
-----------------

None, as the ImageMetaProps object changes have already landed in Ocata [1]_.


REST API impact
---------------

None, as support for BFV instances will be covered in a separate spec.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The tenant user will gain the ability to set a new image meta property against
rescue disk images which will indicate the type of disk bus and device to use
when rescuing instances.

Performance Impact
------------------

None

Other deployer impact
---------------------

If the admin pre-populates any rescue disk images, they may wish to set the
disk bus and device type to override the historic default behaviour.

Developer impact
----------------

Virt driver maintainers can continue to silently ignore the newly introduced
image properties or optionally start using them by implementing this new stable
device approach.

Upgrade impact
--------------

Older Libvirt based computes that are not able to honour the stable device
rescue image properties will continue to silently ignore them as they have
since these were introduced during Ocata [1]_. Once upgraded to Ussuri they
will then start rescusing instances with a stable device layout.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  lyarwood (Libvirt impl)

Other contributors:
  None


Feature Liaison
---------------
lyarwood

Work Items
----------

Extend the compute manager rescue code to handle the full block device mapping
including non-root cinder volume attachments.

Extend the nova Libvirt driver to setup all disks when running in rescue
mode.

Extend the nova Libvirt driver to honour the new image meta properties in
rescue mode disk config.

Dependencies
============

None

Testing
=======

A new tempest Libvirt feature configurable and test will be used to validate
correct operation of the new code.

Documentation Impact
====================

The new image properties should be documented, and any information about
rescue mode should be updated to explain how disks appear.

References
==========

.. [1] hw_rescue_device and hw_rescue_bus image properties https://review.opendev.org/#/c/270285/
.. [2] https://review.opendev.org/#/c/230442/
.. [3] https://review.opendev.org/#/c/273122/
.. [4] https://review.opendev.org/#/c/510106/
.. [5] https://review.opendev.org/#/c/651151/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced [2]_
   * - Newton
     - Reproposed [3]_
   * - Queens
     - Reproposed [4]_
   * - Train
     - Reproposed [5]_
   * - Ussuri
     - Reproposed
