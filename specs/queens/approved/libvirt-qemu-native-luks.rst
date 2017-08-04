..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================================
Libvirt: Native LUKS file and host device decryption by QEMU
============================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-qemu-native-luks

QEMU 2.6 [1]_ and Libvirt 2.2.0 [2]_ allow LUKS files and block
devices to be decrypted natively by QEMU. This spec outlines the required
changes to utilise this new functionality within the Libvirt Nova virt driver
and the possible benefits of doing so.

Problem description
===================

Nova currently supports the use of `LUKS` and `plain` dm-crypt encrypted
volumes using the encryptor classes provided by os-brick. These frontend
encryptor classes use `cryptsetup` to decrypt the encrypted volumes on the
compute host. This creates a decrypted block device on the host that is then
symlinked over the original volume path and attached to an instance.

This use of `cryptsetup` and other external tools has been the source of many
bugs and is an on-going maintenance overhead within Nova and os-brick.

Use Cases
---------

A user should be able to boot from or attach an encrypted LUKS volume of any
file or host block device volume type to an instance without the use of host
command-line utilities such as `cryptsetup` and as a result leaving unencrypted
block devices on the host.

Proposed change
===============

The native LUKS support provided by QEMU 2.6 will be used when a given Libvirt
compute host attempts to attach an encrypted volume with an encryption provider
of `luks` and the required versions of QEMU and Libvirt present on the host.
The required Libvirt disk encryption XML and passphrase secret will then be
created, allowing QEMU to decrypt and attach the volume to the domain.

If the required QEMU and LIbvirt versions are not present Nova will fallback to
the current `LuksEncryptor` encryptor using `cryptsetup` to decrypt the volume.

When detaching, the `LibvirtConfigGuestDisk` object associated with the volume
will be inspected, using the presence of the encryption attribute to confirm
which of the above approaches was used to decrypt the volume.

If this attribute is None the original `cryptsetup` method of detaching the
volume will be used, allowing encrypted volumes to still be detached across
upgrades of Nova, QEMU or Libvirt.

Alternatives
------------

* Continue to use the current `cryptsetup` frontend encryptors.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

* Decrypted block devices will no longer be left on the host as was the case
  with the use of `cryptsetup`, that could result in supposedly encrypted
  tenant data being exposed if the host was compromised.

Notifications impact
--------------------

None

Other end user impact
---------------------

This change should be transparent to existing users of `LuksEncryptor`. Users
should continue to use this encryption provider as before, allowing Nova to
decide when to use the native LUKS support offered by QEMU 2.6 or the
original `cryptsetup` encryptors.

Performance Impact
------------------

None

Other deployer impact
---------------------

Deployers should be made aware that given the required QEMU and Libvirt
versions nova will now use a different method to decrypt encrypted volumes. A
simple releasenote highlighting this change should be sufficient.

Developer impact
----------------

The Libvirt virt driver will have a unique encryptor implementation outside of
those os-brick currently provides.

While this does mean that this implementation is not available to other virt
drivers or OpenStack projects it is difficult to see how it would provide any
benefit outside of the Libvirt virt driver.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  lyarwood

Work Items
----------

* Extend the `nova/virt/libvirt/volumes/` volume drivers to pass the encrypted
  properties of a volume to `LibvirtConfigGuestDisk`.
* Extend the `LibvirtConfigGuestDisk` class to configure the encryption element
  of a disk device [3]_ and to also create the required Libvirt secret for the
  passphrase.
* Only attempt to use QEMU to natively decrypt a given LUKS volume if the
  required QEMU and Libvirt versions are present on the compute host attaching
  the volume.
* Otherwise fallback to the `cryptsetup` encryptors method of decrypting the
  volume.
* Only use `cryptsetup` to detach LUKS volumes if the `LibvirtConfigGuestDisk`
  object associated with the volume is missing the encryption attribute.

Dependencies
============

* QEMU 2.6 [1]_
* Libvirt 2.2.0 [2]_

Both have already been released as part of the Ubuntu 17.04 [4]_ [5]_ [6]_ and
Fedora 25 releases [7]_ [8]_ .

The following devstack change now provides QEMU 2.8 and Libvirt 2.5.0 for
Xenial based OpenStack CI jobs via the Ubuntu Cloud Archive allowing for this
feature to be tested in the gate :

Test using UCA for libvirt 2.5.0
https://review.openstack.org/#/c/451492/

Testing
=======

* Unit tests.
* Existing tempest tests will trigger the use of this new functionality
  if the required versions of Libvirt and QEMU are present.

Documentation Impact
====================

* Limited changes required to the Cinder volume encryption docs [9]_ as
  `cryptsetup` is no longer required on the compute host.

References
==========

.. [1] http://wiki.qemu-project.org/ChangeLog/2.6#Block_devices_2
.. [2] https://libvirt.org/news-2016.html
.. [3] https://libvirt.org/formatstorageencryption.html
.. [4] https://launchpad.net/ubuntu/+source/qemu
.. [5] https://launchpad.net/ubuntu/+source/libvirt
.. [6] https://wiki.ubuntu.com/Releases
.. [7] https://apps.fedoraproject.org/packages/qemu
.. [8] https://apps.fedoraproject.org/packages/libvirt
.. [9] https://docs.openstack.org/cinder/pike/configuration/block-storage/volume-encryption.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
   * - Queens
     - Reproposed
