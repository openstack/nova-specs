..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================================
libvirt driver support for flavor and image defined ephemeral encryption
=========================================================================

https://blueprints.launchpad.net/nova/+spec/ephemeral-storage-encryption

This spec outlines the specific libvirt virt driver implementation to support
the Flavor and Image defined ephemeral storage encryption [1]_ spec.

Problem description
===================

The libvirt virt driver currently provides very limited support for ephemeral
disk encryption through the ``LVM`` imagebackend and the use of the ``PLAIN``
encryption format provided by ``dm-crypt``.

As outlined in the Flavor and Image defined ephemeral storage encryption [1]_
spec this current implementation is controlled through compute host
configurables and is transparent to end users, unlike block storage volume
encryption via Cinder.

With the introduction of the Flavor and Image defined ephemeral storage
encryption [1]_ spec we can now implement support for encrypting ephemeral
disks via images and flavors, allowing support for newer encryption formats
such as `LUKSv1`. This also has the benefit of being natively supported by
`QEMU`, as already seen in the libvirt driver when attaching  `LUKSv1`
encrypted volumes provided by Cinder.

Use Cases
---------

* As a user of a cloud with libvirt based computes I want to request that all
  of my ephemeral storage be encrypted at rest through the selection of a
  specific flavor or image.

* As a user of a cloud with libvirt based computes I want to be able to pick
  how my ephemeral storage be encrypted at rest through the selection of a
  specific flavor or image.

* As a user I want each encrypted ephemeral disk attached to my instance to
  have a separate unique secret associated with it.

* As an operator I want to allow users to request that the ephemeral storage of
  their instances is encrypted using the flexible ``LUKSv1`` encryption format.

Proposed change
===============

Deprecate the legacy implementation within the libvirt driver
-------------------------------------------------------------

The legacy implementation using ``dm-crypt`` within the libvirt virt driver
needs to be deprecated ahead of removal in a future release, this includes the
following options:

* ``[ephemeral_storage_encryption]/enabled``
* ``[ephemeral_storage_encryption]/cipher``
* ``[ephemeral_storage_encryption]/key_size``

Limited support for ``dm-crypt`` will be introduced using the new framework
before this original implementation is removed.

Populate disk_info with encryption properties
---------------------------------------------

The libvirt driver has an additional ``disk_info`` dict built from the contents
of the previously mentioned ``block_device_info`` and image metadata associated
with an instance. With the introduction of the ``DriverImageBlockDevice``
within the Flavor and Image defined ephemeral storage encryption [1]_ spec we
can now avoid the need to look again at image metadata while also adding some
ephemeral encryption related metadata to the dict.

This dict currently contains the following:

``disk_bus``
    The default bus used by disks

``cdrom_bus``
    The default bus used by cd-rom drives

``mapping``
    A nested dict keyed by disk name including information about each disk.

Each item within the ``mapping`` dict containing following keys:

``bus``
    The bus for this disk

``dev``
    The device name for this disk as known to libvirt

``type``
    A type from the BlockDeviceType enum ('disk', 'cdrom','floppy',
    'fs', or 'lun')

It can also contain the following optional keys:

``format``
    Used to format swap/ephemeral disks before passing to instance (e.g.
    'swap', 'ext4')

``boot_index``
    The 1-based boot index of the disk.

In addition to the above this spec will also optionally add the following keys
for encrypted disks:

``encryption_format``
    The encryption format used by the disk

``encryption_options``
    A dict of encryption options

``encryption_secret_uuid``
    The UUID of the encryption secret associated with the disk

Handle ephemeral disk encryption within imagebackend
----------------------------------------------------

With the above in place we can now add encryption support within each image
backend.  As highlighted at the start of this spec this initial support will
only be for the ``LUKSv1`` encryption format.

Generic key management code will be introduced into the base
``nova.virt.libvirt.imagebackend.Image`` class and used to create and store the
encryption secret within the configured key manager. The initial ``LUKSv1``
support will store a passphrase for each disk within the key manager. This is
unlike the current ephemeral storage encryption or encrypted volume
implementations that currently store a symmetric key in the key manager. This
remains a long running piece of technical debt in the encrypted volume
implementation as ``LUKSv1`` does not directly encrypt data with the provided
key.

The base ``nova.virt.libvirt.imagebackend.Image`` class will also be extended
to accept and store the optional encryption details provided by ``disk_info``
above including the format, options and secret UUID.

Each backend will then be modified to encrypt disks during
``nova.virt.libvirt.imagebackend.Image.create_image`` using the provided
format, options and secret.

Enable the ``COMPUTE_EPHEMERAL_ENCRYPTION_LUKS`` trait
------------------------------------------------------

Finally, with the above support in place the ``COMPUTE_EPHEMERAL_ENCRYPTION``
and ``COMPUTE_EPHEMERAL_ENCRYPTION_LUKS`` traits can be enabled when using a
backend that supports ``LUKSv1``. This will in turn enable scheduling to the
compute of any user requests asking for ephemeral storage encryption using the
format.

Alternatives
------------

Continue to use the transparent host configurables and expand support to other
encryption formats such as ``LUKS``.

Data model impact
-----------------

As discussed above the ephemeral encryption keys will be added to the disk_info
for individual disks within the libvirt driver.

REST API impact
---------------

N/A

Security impact
---------------

This should hopefully be positive given the unique secret per disk and user
visible choice regarding how their ephemeral storage is encrypted at rest.

Notifications impact
--------------------

N/A

Other end user impact
---------------------

Users will now need to opt-in to ephemeral storage encryption being used by
their instances through their choice of image or flavors.

Performance Impact
------------------

QEMU will natively decrypt these ``LUKSv1`` ephemeral disks for us using the
``libgcrypt`` library. While there have been performance issues with this in
the past workarounds [2]_ can be implemented that use ``dm-crypt`` instead.

Other deployer impact
---------------------

N/A

Developer impact
----------------

This spec will aim to implement ``LUKSv1`` support for all imagebackends but in
the future any additional encryption formats supported by these backends will
need to ensure matching traits are also enabled.

Upgrade impact
--------------

The legacy implementation is deprecated but will continue to work for the time
being. As the new implementation is separate there is no further upgrade
impact.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    lyarwood

Other contributors:
    N/A

Feature Liaison
---------------

Feature liaison:
    lyarwood

Work Items
----------

* Populate the individual disk dicts within ``disk_info`` with any
  ephemeral encryption properties.

* Provide these properties to the imagebackends when creating each disk.

* Introduce support for ``LUKSv1`` based encryption within the imagebackends.

* Enable the ``COMPUTE_EPHEMERAL_ENCRYPTION_LUKS`` trait when the selected
  imagebackend supports ``LUKSv1``.

Dependencies
============

* Flavor and Image defined ephemeral storage encryption [1]_

Testing
=======

Unlike the parent spec once imagebackends support ``LUKSv1`` and enable the
required trait we can introduce Tempest based testing of this implementation in
addition to extensive functional and unit based tests.

Documentation Impact
====================

* New user documentation around the specific ``LUKSv1`` support for ephemeral
  encryption within the libvirt driver.

* Reference documentation around the changes to the virt block device layer.

References
==========

.. [1] https://specs.openstack.org/openstack/nova-specs/specs/yoga/approved/ephemeral-encryption.html
.. [2] https://docs.openstack.org/nova/victoria/configuration/config.html#workarounds.disable_native_luksv1

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
   * - Yoga
     - Reproposed
