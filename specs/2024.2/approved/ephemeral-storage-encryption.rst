..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Flavor and Image defined ephemeral storage encryption
=====================================================

https://blueprints.launchpad.net/nova/+spec/ephemeral-storage-encryption

This spec outlines a new approach to ephemeral storage encryption in Nova
allowing users to select how their ephemeral storage is encrypted at rest
through the use of flavors with specific extra specs or images with specific
properties. The aim being to bring the ephemeral storage encryption experience
within Nova in line with the block storage encryption implementation provided
by Cinder where user selectable `encrypted volume types`_ are available.

.. note::

   This spec will only cover the high level changes to the API and compute
   layers, implementation within specific virt drivers is left for separate
   specs.

-------------------
Problem description
-------------------

At present the only in-tree ephemeral storage encryption support is provided by
the libvirt virt driver when using the lvm imagebackend. The current
implementation provides basic operator controlled and configured host specific
support for ephemeral disk encryption at rest where all instances on a given
compute are forced to use encrypted ephemeral storage using the dm-crypt
``PLAIN`` encryption format.

This is not ideal and makes ephemeral storage encryption completely opaque
to the end user as opposed to the block storage encryption support provided by
Cinder where users are able to opt-in to using admin defined encrypted volume
types to ensure their storage is encrypted at rest.

Additionally the current implementation uses a single symmetric key to encrypt
all ephemeral storage associated with the instance. As the ``PLAIN`` encryption
format is used there is no way to rotate this key in-place.

Use Cases
=========

* As a user I want to request that all of my ephemeral storage is encrypted
  at rest through the selection of a specific flavor or image.

* As a user I want to be able to pick how my ephemeral storage is encrypted
  at rest through the selection of a specific flavor or image.

* As an admin/operator I want to either enforce ephemeral encryption per flavor
  or per image.

* As an admin/operator I want to provide sane choices to my end users regarding
  how their ephemeral storage is encrypted at rest.

* As a virt driver maintainer/developer I want to indicate that my driver
  supports ephemeral storage encryption using a specific encryption format.

* As a virt driver maintainer/developer I want to provide sane default
  encryption format and options for users looking to encrypt their ephemeral
  storage at rest. I want these associated with the encrypted storage until it
  is deleted.

---------------
Proposed change
---------------

To enable this new flavor extra specs, image properties and host configurables
will be introduced. These will control when and how ephemeral storage
encryption at rest is enabled for an instance.

.. note::

   The following ``hw_ephemeral_encryption`` image properties do not relate to
   if an image is encrypted at rest within the Glance service. They only relate
   to how ephemeral storage will be encrypted at rest when used by a
   provisioned instance within Nova.

Allow ephemeral encryption to be configured by flavor, image, or config
=======================================================================

To enable ephemeral encryption per instance the following boolean based flavor
extra spec and image property will be introduced:

* ``hw:ephemeral_encryption``
* ``hw_ephemeral_encryption``

The above will enable ephemeral storage encryption for an instance but does not
control the encryption format used. For this, a configuration option will be
used to provide a default format per compute which will initially default to
``luks`` with no other choices at this time.

* ``[ephemeral_storage_encryption]/default_format``

To enable snapshot and shelve of instances using ephemeral encryption, the UUID
of the encryption secret and the encryption format for the resultant image will
be kept with the image using the standardized Glance image properties |Glance
spec|_:

* ``os_encrypt_key_id``
* ``os_encrypt_format``

The secret UUID and encryption format are needed when creating an instance from
an ephemeral encrypted snapshot or when unshelving an ephemeral encrypted
instance.

The other ``os_encrypt*`` Glance image properties will also be set at the time
of snapshot:

* ``os_encrypt_cipher`` - the cipher algorithm, e.g. 'AES256'
* ``os_encrypt_key_deletion_policy`` - on image deletion indicates whether the
  key should be deleted too
* ``os_decrypt_container_format`` - format change, e.g. from 'compressed' to
  'bare'
* ``os_decrypt_size`` - size after payload decryption

.. |Glance spec| replace:: [1]

Possible future work
--------------------

In the future, we could consider supporting a cloud with a mix of compute hosts
providing either LUKSv1 (qcow2|raw|rbd) or legacy dm-crypt PLAIN (LVM)
encryption formats.

The encryption format used would be controlled by the following flavor extra
specs and image properties:

* ``hw:ephemeral_encryption_format``
* ``hw_ephemeral_encryption_format``

and would be used to schedule to a compute host which supports the specified
format.

The format would be provided as a string that maps to a
``BlockDeviceEncryptionFormatTypeField`` oslo.versionedobjects field value:

* ``legacy_dmcrypt_plain`` for the dm-crypt PLAIN format
* ``luks``  for the LUKSv1 format

and if neither are specified, the format would be taken from the
``os_encrypt_format`` |Glance spec|_ if the source image is encrypted. If the
source image is not encrypted, the format would be taken from
``[ephemeral_storage_encryption]/default_format`` after an instance lands on a
compute host.

Management of secret data with the Key Manager service
======================================================

The passphrases of encrypted disks are managed using a Key Manager service such
as Barbican_.

Nova will create, retrieve, and delete disk passphrases using the authorization
token of the user calling Nova API. The cloud operator must consider the
implications of secret ownership with regard to server actions and who is
allowed to perform them::

    ┌─────────────────────┐                        ┌────────────────────┐
    │                     │                        │                    │
    │                     │                        │                    │
    │       Nova API      │◄───────────────────────┤    Barbican API    │
    │                     │                        │                    │
    │                     ├─────┬────────────┬────►│                    │
    │                     │     │ User token │     │                    │
    │                     │     └────────────┘     │                    │
    │                     │                        │                    │
    └──────────▲──────────┘                        └────────────────────┘
               │
               │
               │
               │
               │
  ┌────────────┤
  │ User token │
  └────────────┤
               │
               │
               │
               │
          ┌─────────┐
          │         │
          │  User   │
          │         │
          └─────────┘

By default, Barbican scopes the ownership of a secret at the project level.
This means that many calls in the Barbican API will perform an additional check
to ensure that the ``project_id`` of the token matches the ``project_id``
stored as the secret owner. Users who are members of the same project have
access to each other's secrets in this configuration.

For admin-only APIs such as cold migrate, live migrate, and evacuate, the
user calling Nova API to perform these server actions needs both:

#. Access the Barbican secrets of the owner of the server

#. The ``admin`` role in order to call admin-only Nova APIs such as cold
   migration, live migration, evacuate, etc

In a default Barbican configuration, secret ownership will be scoped to the
project which created it, so in such an environment a user would need to be a
`project administrator`_ or any user who has both project membership and the
``admin`` role.

Note that it is possible for cloud operators to implement more fine-grained
control of secrets in Barbican using `access control lists`_. Secrets could be
made to be scoped at the user level, for example, instead of at the project
level. In such a configuration, a `project administrator`_,  would **not** be
allowed perform admin-only API server actions on a server belonging to a
different user in the project.

Operators must plan ahead to determine what configuration and access control of
Barbican secrets they need in their environments.

.. important::

   For legacy deployments using ``[oslo_policy]enforce_scope = False`` in their
   service configuration files, an additional step is required to allow
   users to create servers with encrypted local disks.

   In a legacy deployment, users must have the ``creator`` role or the
   ``admin`` role assigned to them in Keystone in order to be allowed to
   create secrets in the Barbican key manager service. Otherwise, user requests
   to create servers with encrypted local disks will fail.

   .. code-block:: console
      :emphasize-lines: 7

      $ openstack role list
      +----------------------------------+---------------------------+
      | ID                               | Name                      |
      +----------------------------------+---------------------------+
      | 068b4910f0eb4a1cb6a4a2a1e94c3dfe | reader                    |
      | 25dc4ed8f3814fd1941a580d78f2b635 | service                   |
      | 7e832eeb2c2842c9b03c376bf3113247 | creator                   |
      | 59df386beb0f460095b7622fc1a45e22 | member                    |
      | 655bbf1b9f844399bcfbfbbef4248045 | admin                     |
      +----------------------------------+---------------------------+

.. _Barbican: https://docs.openstack.org/barbican/latest/index.html
.. _access control lists: https://docs.openstack.org/barbican/latest/admin/access_control.html
.. _project administrator: https://docs.openstack.org/keystone/latest/admin/service-api-protection.html#project-administrators

Create a new key manager secret for each block device mapping
=============================================================

The approach for disk image secrets is that each disk image has a unique
secret.

For example:

Let's say ``Instance A`` has 3 disks: one root disk, one ephemeral disk, and
one swap disk. Each disk will have its own secret.

With qcow2, if an instance is created from an encrypted source image, the
resulting backing file will have the same passphrase as the source image in
order for the backing file to be shared among multiple instances. For each
instance sharing the backing file, the instance has its own "copy" of the
secret (a new Barbican secret that has the same passphrase).

This prevents a single point of failure with regard to Barbican secret
deletion. For example, if 100 instances share the same encrypted backing file
and a user mistakenly deletes a Barbican secret for the backing file, only one
instance or image will be affected. If one Barbican secret were shared by the
100 instances using the same encrypted backing file, 100 instances and the
source image would be affected.

Barbican does have a reference counting API for secret consumers which
increments and decrements an internal counter over HTTP. If the count for a
given secret becomes incorrectly zero for any reason, over time, (race
conditions, etc), the API will allow deletion of that secret even if it is in
use.

This table is intended to illustrate the way secrets are handled in various
scenarios.

.. table::
   :align: left

   +--------------------+-------------+--------------------------------------+------------------------------------------------------+
   | Instance or Image  | Disk        | Secret                               | Notes                                                |
   |                    |             | (passphrase)                         |                                                      |
   +====================+=============+======================================+======================================================+
   | Instance A         | disk (root) | Secret 1                             | Secret 1, 2, and 3 will be automatically deleted     |
   |                    +-------------+--------------------------------------+ by Nova when Instance A is deleted and its disks are |
   |                    | disk.eph0   | Secret 2                             | destroyed                                            |
   |                    +-------------+--------------------------------------+                                                      |
   |                    | disk.swap   | Secret 3                             |                                                      |
   +--------------------+-------------+--------------------------------------+------------------------------------------------------+
   | Image Z (snapshot) | disk (root) | Secret 4                             | Secret 4 will **not** be automatically deleted and   |
   | created from       |             | (copy of Secret 1 by default)        | manual deletion will be needed if/when Image Z is    |
   | Instance A         |             |                                      | deleted from Glance                                  |
   +--------------------+-------------+--------------------------------------+------------------------------------------------------+
   | Instance B         | disk (root) | Secret 5 :sup:`*` (copy of Secret 4) | Secret 5, 6, 7, and 8 will be automatically deleted  |
   | created from       |             +--------------------------------------+ by Nova when Instance B is deleted and its disks are |
   | Image Z (snapshot) |             | Secret 6                             | destroyed                                            |
   |                    +-------------+--------------------------------------+                                                      |
   |                    | disk.eph0   | Secret 7                             |                                                      |
   |                    +-------------+--------------------------------------+                                                      |
   |                    | disk.swap   | Secret 8                             |                                                      |
   +--------------------+-------------+--------------------------------------+------------------------------------------------------+
   | Instance C         | disk (root) | Secret 9                             | Secret 9, 10, and 11 will be automatically deleted   |
   |                    +-------------+--------------------------------------+ by Nova when Instance C is deleted and its disks are |
   |                    | disk.eph0   | Secret 10                            | destroyed                                            |
   |                    +-------------+--------------------------------------+                                                      |
   |                    | disk.swap   | Secret 11                            |                                                      |
   +--------------------+-------------+--------------------------------------+------------------------------------------------------+
   | Image Y (snapshot) | disk (root) | Secret 9                             | Secret 9 is **reused** when Instance C is shelved    |
   | created by shelve  |             |                                      | in part to prevent the possibility of a change in    |
   | of Instance C      |             |                                      | ownership of the root disk secret if, for example,   |
   |                    |             |                                      | an admin user shelves a non-admin user's instance.   |
   |                    |             |                                      | This approach could be avoided if there is some way  |
   |                    |             |                                      | we could create a new secret using the instance's    |
   |                    |             |                                      | user/project rather than the shelver's user/project  |
   +--------------------+-------------+--------------------------------------+------------------------------------------------------+
   | Rescue disk        | disk (root) | None                                 | A rescue disk is only encrypted if an encrypted      |
   | created by rescue  |             |                                      | rescue image was specified.                          |
   | of Instance A      |             |                                      |                                                      |
   +--------------------+-------------+--------------------------------------+------------------------------------------------------+
   | Rescue disk        | disk (root) | Secret of encrypted rescue image     | The secret of the encrypted rescue image will be     |
   | created by rescue  |             |                                      | reused and no new secrets will be created or deleted |
   | of Instance A      |             |                                      |                                                      |
   | using encrypted    |             |                                      |                                                      |
   | rescue image       |             |                                      |                                                      |
   +--------------------+-------------+--------------------------------------+------------------------------------------------------+

:sup:`*` backing file secret for qcow2 only

Encrypted source images
=======================

The default behavior when creating an instance from an encrypted source image
will be to create encrypted disks. The reasoning is that we aim to avoid
"surprise" decryption of images and that decryption should be something that a
user or flavor or image has to opt-in to and explicitly request so the intent
is clear.

Encrypted source images will have the ``os_encrypt_key_id``,
``os_encrypt_format``, and other |Glance spec|_ image properties in their image
metadata.  Access to the secret of the encrypted source image is determined by
the key manager API policy and/or access control lists.

At this time, we expect to use a subset of the standardized image properties:

    * ``os_encrypt_format`` - to know how to interpret the image format
    * ``os_encrypt_key_id`` - to copy/convert/etc the source image if needed

When creating an instance with encrypted disks from an encrypted source image
when ``hw_ephemeral_encryption`` has not been set, we will either use the
presence of the automatically stored ``image_os_encrypt_key_id`` in system
metadata or potentially store ``image_hw_ephemeral_encryption=true`` in the
instance system metadata and use it to ensure an instance will be scheduled to
a compute host which supports ephemeral encryption.

If the ``os_encrypt_key_id`` image property is set on the encrypted image and
the image or flavor also has ``hw_ephemeral_encryption=false`` or
``hw:ephemeral_encryption=false`` explicitly set, we will reject the API
request with a 409 conflict error at this time.

We could consider future work to interpret the aforementioned combination of
image property settings as an intentional request to create an instance with
unencrypted disks from the encrypted source image and perform the decryption.

Encrypted backing files (qcow2)
===============================

The approach regarding backing files is that they will be encrypted if the
source image from which it was created is encrypted. If the source image from
which the disk is created is not encrypted, the backing file stored internally
in Nova will also not be encrypted. If the source image is encrypted, the
backing file will also be encrypted.

An encrypted backing file uses the same passphrase as the source image from
which it was created. This is required for the encrypted backing file to be
shared among multiple instances in the same project.

Backing files for ephemeral disks and swap disks are never encrypted as they
are always created from blank disks.

Snapshots of instances with ephemeral encryption
================================================

When an instance with ephemeral encryption is snapshotted, the behavior for
encrypting the image snapshot is determined by request parameters which will
be added to the snapshot API.

The API request parameters are intended to support workflows that involve
sharing of encrypted image snapshots with other projects or users.

Examples:

* An instance owner wants to back up their disk

* An instance owner wants to make a copy of their disk that is encrypted with
  a new key

* An instance owner wants to make a copy of their disk using an existing key
  that belongs to a different project or user (provided that project or user
  has created the necessary `access control list`_ for the secret)

* An instance owner wants to create an unencrypted public copy of their disk

* An instance owner with an unencrypted disk wants to make an encrypted copy to
  facilitate secure exfiltration of their disk to another location

New API microversion for Create Image (createImage Action)
----------------------------------------------------------

A new microversion will be added to the `create image API`_ to support
ephemeral encryption options. Users will be able to choose how they want
encryption of the new image snapshot to be handled. They can use the same key
as the image being snapshotted (the default), have Nova generate a new key
and use it to encrypt the image snapshot, provide their own key secret UUID
to use to encrypt the image snapshot, or not encrypt the image snapshot at
all.

Request for ``POST /servers/{server_id}/action`` with ``createImage``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Request
   :align: left
   :widths: 20, 5, 5, 70
   :header-rows: 1

   * - Name
     - In
     - Type
     - Description
   * - server_id
     - path
     - string
     - The UUID of the server.
   * - createImage
     - body
     - object
     - The action to create a snapshot of the image or the volume(s) of the
       server.
   * - name
     - body
     - string
     - The display name of an Image.
   * - metadata (Optional)
     - body
     - object
     - Metadata key and value pairs for the image. The maximum size for each
       metadata key and value pair is 255 bytes.
   * - encryption (Optional)
     - body
     - object
     - Encryption options for the image to create. These options apply only to
       encrypted local disks.
   * - encryption.key
     - body
     - string
     - The key to use to encrypt the image snapshot. Valid values are:

       * ``same``: Use the same key to encrypt the image snapshot.
         This is the default.

       * ``new``: Generate a new key and use it to encrypt the image snapshot.

       * ``existing``: The user will provide the UUID of an existing secret in
         the key manager service to use to encrypt the image snapshot.

       * ``none``: Do not encrypt the image snapshot.
   * - encryption.secret_uuid (Optional)
     - body
     - string
     - The UUID of the key manager service secret that was used to encrypt the
       image snapshot.

.. code-block:: json
   :emphasize-lines: 7-10

   {
       "createImage" : {
           "name" : "foo-image",
           "metadata": {
               "meta_var": "meta_val"
           },
           "encryption": {
               "key": "same|new|existing|none",
               "secret_uuid": "<secret uuid> if 'key' is 'existing', or absent"
           }
       }
   }

Request choices for encryption.key:

``same``
   Use the same key to encrypt the new disk image. This is the default.

``new``
   Generate a new key to encrypt the new disk image.

``existing``
   Use the provided ``<secret uuid>`` to encrypt the new disk image.

``none``
   Do not encrypt the new disk image.


.. note::

    Ceph release Quincy (v17) and older do not support creating a cloned image
    with an encryption key different from its parent. For this reason, the
    ``encryption.key`` request parameter with a value of ``new`` will not be
    supported with the ``rbd`` image backend for those versions of Ceph.

    The plan if a user requests a snapshot with ``encryption.key`` and ``new``
    and Ceph <= Quincy (v17), the snapshot server action will be marked as
    failed with a message that explains that ``new`` is not supported in the
    deployment.

    See https://github.com/ceph/ceph/commit/1d3de19 for reference.

Response for ``POST /servers/{server_id}/action`` with ``createImage``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(There will be no change to the response parameters.)

.. list-table:: Response
   :align: left
   :widths: 20, 5, 5, 70
   :header-rows: 1

   * - Name
     - In
     - Type
     - Description
   * - image_id
     - body
     - string
     - The UUID for the resulting image snapshot.

.. code-block:: json

   {
      "image_id": "0e7761dd-ee98-41f0-ba35-05994e446431",
   }

.. _`create image API`: https://docs.openstack.org/api-ref/compute/#create-image-createimage-action
.. _`access control list`: https://docs.openstack.org/barbican/latest/admin/access_control.html

Create Server Back Up (createBackup Action) API
-----------------------------------------------

The ``POST /servers/{server_id}/action`` API with ``createBackup`` will not be
changed. Image snapshots created by this API will be encrypted using the same
key.


Image metadata for image snapshots of encrypted disks
-----------------------------------------------------

When an encrypted image snapshot is created, its image properties will be set
to contain encryption information when Nova uploads it to Glance. There is a
`Glance spec`_ proposed to establish a set of standardized image properties for
all projects to use when working with encrypted Glance images:

    * ``os_encrypt_format`` - the main mechanism used, e.g. 'LUKS'
    * ``os_encrypt_cipher`` - the cipher algorithm, e.g. 'AES256'
    * ``os_encrypt_key_id`` - reference to key in the key manager
    * ``os_encrypt_key_deletion_policy`` - on image deletion indicates whether
          the key should be deleted too
    * ``os_decrypt_container_format`` - format after payload decryption, e.g.
          'qcow'
    * ``os_decrypt_size`` - size after payload decryption

and will be used for snapshots of encrypted images in Nova.

When a new instance is created from an encrypted image, the image properties
are passed down to the lower layers by their presence in the instance's system
metadata with ``image_`` prefix. The system metadata is used because at the
lower layers (where ``qemu-img convert`` is called, for example) we no longer
have access to the image metadata and nontrivial refactoring to pass image
metadata to several lower layer methods, or similar, would be required
otherwise.

.. _`Glance spec`:  https://review.opendev.org/c/openstack/glance-specs/+/915726

Snapshots created by shelving instances with ephemeral encryption
=================================================================

When an instance with ephemeral encryption is shelved, the existing root disk
encryption secret is **reused** and will be used to unshelve the instance
later. This is done to prevent a potential change in ownership of the root disk
encryption secret in a scenario where an admin user shelves a non-admin user's
instance, for example. If a new secret were created owned by the admin user,
the non-admin user who owns the instance would be unable to unshelve the
instance.

This behavior could be avoided however if there is some way we could create a
new encryption secret using the instance's user and project rather than the
shelver's user and project. If that were possible, we would not need to reuse
the encryption secret.

Rescue disk images created when the rescue image is encrypted
=============================================================

When rescuing an instance and an encrypted rescue image is specified, the
rescue image secret UUID from the image property will be used to encrypt the
rescue disk. A new key manager secret will not be created.

The rescue image secret is used because it will exist whether the instance has
an encrypted root disk or not. It is technically possible to specify an
encrypted rescue image for an instance that does not otherwise have encrypted
local disks.

The rescue disk will be encrypted if and only if the rescue image is encrypted,
with the objective of not creating unencrypted data at rest from data that is
currently encrypted at rest.

The new virt driver secret will be created for the rescue disk and is deleted
when the instance is unrescued.

Cleanup of ephemeral encryption secrets
=======================================

Ephemeral encryption secrets are deleted from the key manager and the virt
driver when the corresponding instance is deleted and its disks are destroyed.

Virt driver secrets may be created on destination hosts and deleted from source
hosts as needed during instance migrations.

Key manager secrets are however **only** deleted when the disks associated with
them are destroyed.

Encryption secrets that are created when a snapshot is created are **never**
deleted by Nova. It would only be acceptable to delete the secret if and when
the image snapshot is deleted from Glance. There is a
``os_encrypt_deletion_policy`` image property proposed in the standardized
Glance image properties that Nova will set to tell Glance to go ahead and
delete the key manager secret for the image at the same time the image is
deleted.

BlockDeviceMapping changes
==========================

The ``BlockDeviceMapping`` object will be extended to include the following
fields encapsulating some of the above information per ephemeral disk within
the instance:

``encrypted``
    A simple boolean to indicate if the block device is encrypted. This will
    initially only be populated when ephemeral encryption is used but could
    easily be used for encrypted volumes as well in the future.

``encryption_secret_uuid``
    As the name suggests this will contain the UUID of the associated
    encryption secret for the disk. The type of secret used here will be
    specific to the encryption format and virt driver used, it should not be
    assumed that this will always been an symmetric key as is currently the
    case with all encrypted volumes provided by Cinder. For example, for
    ``luks`` based ephemeral storage this secret will be a ``passphrase``.

``backing_encryption_secret_uuid``
    This will contain the UUID of the associated encryption secret for the
    backing file for the disk in the case of qcow2.

``encryption_format``
    A new ``BlockDeviceEncryptionFormatType`` enum and associated
    ``BlockDeviceEncryptionFormatTypeField`` field listing the encryption
    format. The available options being kept in line with the constants
    currently provided by os-brick and potentially merged in the future if both
    can share these types and fields somehow.

``encryption_options``
    A simple unversioned dict of strings containing encryption options specific
    to the virt driver implementation, underlying hypervisor and format being
    used.

.. note::

   The ``encryption_options`` field may be used to store the encryption
   parameters that were used to create the disk such as cipher algorithm,
   cipher mode, and initialization vector generator algorithm.

   The intention will be to be able to track the encryption attributes of each
   disk to aid in handling future upgrade scenarios such as removal of an
   algorithm or a change in a default in QEMU.

Populate ephemeral encryption BlockDeviceMapping attributes during build
========================================================================

When launching an instance with ephemeral encryption requested via either the
image or flavor the ``BlockDeviceMapping.encrypted`` attribute will be set to
``True`` for each ``BlockDeviceMapping`` record with a ``destination_type``
value of ``local``. This will happen after the original API BDM dicts have been
transformed into objects within the Compute API but before scheduling the
instance(s).

The ``encryption_format`` attribute will also take its value from the image or
flavor if provided. Any differences or conflicts between the image and flavor
for this will raise a ``409 Conflict`` error being raised by the API.

Use ``COMPUTE_EPHEMERAL_ENCRYPTION`` compatibility traits
=========================================================

A ``COMPUTE_EPHEMERAL_ENCRYPTION`` compute compatibility trait was introduced
during `Wallaby`__ and will be reported by virt drivers to indicate overall
support for ephemeral storage encryption using this new approach. This trait
will always be used by pre-filter outlined in the following section when
ephemeral encryption has been requested, regardless of any format being
specified in the request, allowing the compute that eventually handles the
request to select a format it supports using the
``[ephemeral_storage_encryption]/default_format`` configurable.

.. __: https://review.opendev.org/c/openstack/os-traits/+/759878

``COMPUTE_EPHEMERAL_ENCRYPTION_$FORMAT`` compute compatibility traits were also
added to os-traits during Wallaby and will be reported by virt drivers to
indicate support for specific ephemeral storage encryption formats. For
example:


* ``COMPUTE_EPHEMERAL_ENCRYPTION_LUKS``
* ``COMPUTE_EPHEMERAL_ENCRYPTION_LUKSV2``
* ``COMPUTE_EPHEMERAL_ENCRYPTION_PLAIN``

These traits will only be used alongside the ``COMPUTE_EPHEMERAL_ENCRYPTION``
trait when the ``hw_ephemeral_encryption_format`` image property or
``hw:ephemeral_encryption_format`` extra spec have been provided in the initial
request.

Introduce an ephemeral encryption request pre-filter
====================================================

A new pre-filter will be introduced that adds the above traits as required to
the request spec when the aforementioned image properties or flavor extra specs
are provided. As outlined above this will always include the
``COMPUTE_EPHEMERAL_ENCRYPTION`` trait when ephemeral encryption has been
requested and may optionally include one of the format specific traits if a
format is included in the request.

Expose ephemeral encryption attributes via block_device_info
============================================================

Once the ``BlockDeviceMapping`` objects have been updated and the instance
scheduled to a compute the objects are transformed once again into a
``block_device_info`` dict understood by the virt layer that at present
contains the following:

``root_device_name``
    The root device path used by the instance.

``ephemerals``
    A list of ``DriverEphemeralBlockDevice`` dict objects detailing the
    ephemeral disks attached to the instance. Note this does not include the
    initial image based disk used by the instance that is classified as an
    ephemeral disk in terms of the ephemeral encryption feature.

``block_device_mapping``
    A list of ``DriverVol*BlockDevice`` dict objects detailing the volume based
    disks attached to the instance.

``swap``
    An optional ``DriverSwapBlockDevice`` dict object detailing the swap
    device.


For example:

.. code-block:: json

    {
        "root_device_name": "/dev/vda",
        "ephemerals": [
            {
                "guest_format": null,
                "device_name": "/dev/vdb",
                "device_type": "disk",
                "size": 1,
                "disk_bus": "virtio"
            }
        ],
        "block_device_mapping": [],
        "swap": {
            "swap_size": 1,
            "device_name": "/dev/vdc",
            "disk_bus": "virtio"
        }
    }

As noted above ``block_device_info`` does not provide a complete overview of
the storage associated with an instance. In order for it to be useful in the
context of ephemeral storage encryption we would need to extend the dict to
always include information relating to local image based disks.

As such a new ``DriverImageBlockDevice`` dict class will be introduced covering
image based block devices and provided to the virt layer via an additional
``image`` key within the ``block_device_info`` dict when the instance uses such
a disk. As with the other ``Driver*BlockDevice`` dict classes this will proxy
access to the underlying ``BlockDeviceMapping`` object allowing the virt layer
to lookup the previously listed ``encrypted`` and ``encryption_*`` attributes.

While outside the scope of this spec the above highlights a huge amount of
complexity and technical debt still residing in the codebase around how storage
configurations are handled between the different layers. In the long term we
should plan to remove ``block_device_info`` and replace it with direct access
to ``BlockDeviceMapping`` based objects ensuring the entire configuration is
always exposed to the virt layer.

Report that a disk is encrypted at rest through the metadata API
================================================================

Extend the metadata API so that users can confirm that their ephemeral storage
is encrypted at rest through the metadata API, accessible from within their
instance.

.. code-block:: json

    {
        "devices": [
            {
                "type": "nic",
                "bus": "pci",
                "address": "0000:00:02.0",
                "mac": "00:11:22:33:44:55",
                "tags": ["trusted"]
            },
            {
                "type": "disk",
                "bus": "virtio",
                "address": "0:0",
                "serial": "12352423",
                "path": "/dev/vda",
                "encrypted": "True"
            },
            {
                "type": "disk",
                "bus": "ide",
                "address": "0:0",
                "serial": "disk-vol-2352423",
                "path": "/dev/sda",
                "tags": ["baz"]
            }
        ]
    }

This should also be extended to cover disks provided by encrypted volumes but
this is obviously out of scope for this implementation.

Block resize between flavors with different ``hw:ephemeral_encryption`` values
==============================================================================

Ephemeral data is expected to persist through a resize and as such any resize
between flavors that differed in their configuration of ephemeral encryption
(one enabled, another disabled or formats etc) would cause us to convert this
data in place. This isn't trivial and so for this initial implementation
resizing between flavors that differ will be blocked.

Support for resizing between flavors with different ephemeral encryption
parameters is planned to be added in a separate patch later in the series.

Provide a migration path from the legacy implementation
=======================================================

New ``nova-manage`` and ``nova-status`` commands will be introduced to migrate
any instances using the legacy libvirt virt driver implementation ahead of the
removal of this in a future release.

The ``nova-manage`` command will ensure that any existing instances with
``ephemeral_key_uuid`` set will have their associated ``BlockDeviceMapping``
records updated to reference said secret key, the ``legacy_dmcrypt_plain``
encryption format and configured options on the host before clearing
``ephemeral_key_uuid``.

Additionally the libvirt virt driver will also attempt to migrate instances
with ``ephemeral_key_uuid`` set during spawn. This should allow at least some
of the instances to be moved during the W release ahead of X.

The ``nova-status`` command will simply report on the existence of any
instances with ``ephemeral_key_uuid`` set that do not have the corresponding
``BlockDeviceMapping`` attributes enabled etc.

Deprecate the now legacy implementation
=======================================

The legacy implementation within the libvirt virt driver will be deprecated for
removal in a future release once the ability to migrate is in place.

Alternatives
============

Continue to use the transparent host configurables and expand support to other
encryption formats such as ``LUKS``.

Data model impact
=================

See above for the various flavor extra spec, image property,
``BlockDeviceMapping`` and ``DriverBlockDevice`` object changes.

REST API impact
===============

* A new API microversion will be created to add encryption options to the
  ``createImage`` server action API.

* Flavor extra specs and image property validation will be introduced for the
  any ephemeral encryption provided options.

* Attempts to resize between flavors that differ in their ephemeral encryption
  options will be rejected.

* Attempts to rebuild between images that differ in their ephemeral encryption
  options will be allowed by the user who owns the instance. Requests to
  rebuild between images that differ in their ephemeral encryption options will
  be rejected. This is to prevent a change in the ownership of secrets for the
  instance disks.

* The metadata API will be changed to allow users to determine if their
  ephemeral storage is encrypted as discussed above.

Security impact
===============

This should hopefully be positive given the unique secret per disk and user
visible choice regarding how their ephemeral storage is encrypted at rest.

Additionally this should allow additional virt drivers to support ephemeral
storage encryption while also allowing the libvirt virt driver to increase
coverage of the feature across more image backends such as qcow2 and rbd.

Notifications impact
====================

N/A

Other end user impact
=====================

Users may be able to opt-in to ephemeral storage encryption being used by
their instances through their choice of image or flavor.

Performance Impact
==================

The additional pre-filter will add a small amount of overhead when scheduling
instances but this should fail fast if ephemeral encryption is not requested
through the image or flavor.

The performance impact of increased use of ephemeral storage encryption by
instances is left to be discussed in the virt driver specific specs as this
will vary between hypervisors.

Other deployer impact
=====================

N/A

Developer impact
================

Virt driver developers will be able to indicate support for specific ephemeral
storage encryption formats using the newly introduced compute compatibility
traits.

Upgrade impact
==============

The compute traits should ensure that requests to schedule instances using
ephemeral storage encryption with mixed computes (N-1 and N) will work during a
rolling upgrade.

As discussed earlier in the spec future upgrades will need to provide a path
for existing ephemeral storage encryption users to migrate from the legacy
implementation. This should be trivial but may require an additional grenade
based job in CI during the W cycle to prove out the migration path.

--------------
Implementation
--------------

Assignee(s)
===========

Primary assignee:
    melwitt

Other contributors:
    lyarwood

Feature Liaison
===============

Feature liaison:
    melwitt

Work Items
==========

* Introduce ``hw_ephemeral_encryption`` image properties and
  ``hw:ephemeral_encryption`` flavor extra specs.

* Introduce a new ``encrypted``. ``encryption_secret_uuid``,
  ``backing_encryption_secret_uuid``, ``encryption_format`` and
  ``encryption_options`` attributes to the BlockDeviceMapping Object.

* Wire up the new ``BlockDeviceMapping`` object attributes through the
  ``Driver*BlockDevice`` layer and ``block_device_info`` dict.

* Report ephemeral storage encryption through the metadata API.

* Introduce new ``nova-manage`` and ``nova-status`` commands to allow existing
  users to migrate to this new implementation. This should however be blocked
  outside of testing until a virt driver implementation is landed.

* Validate all of the above in functional tests ahead of any virt driver
  implementation landing.

------------
Dependencies
------------

None

-------
Testing
-------

At present without a virt driver implementation this will be tested entirely
within our unit and functional test suites.

Once a virt driver implementation is available additional integration tests in
Tempest and whitebox tests can be written.

Testing of the migration path from the legacy implementation will require an
additional grenade job but this will require the libvirt virt driver
implementation to be completed first.

--------------------
Documentation Impact
--------------------

* The new host configurables, flavor extra specs and image properties should be
  documented.

* New user documentation should be written covering the overall use of the
  feature from a Nova point of view.

* Reference documentation around `BlockDeviceMapping` objects etc should be
  updated to make note of the new encryption attributes.

----------
References
----------

* https://review.opendev.org/c/openstack/glance-specs/+/915726

.. _`encrypted volume types`: https://docs.openstack.org/cinder/latest/configuration/block-storage/volume-encryption.html#create-an-encrypted-volume-type
.. _`libvirt virt driver`: https://libvirt.org/formatstorageencryption.html#StorageEncryptionLuks

-------
History
-------

.. list-table:: Revisions
   :align: left
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
   * - Xena
     - Reproposed
   * - Yoga
     - Reproposed
   * - Zed
     - Reproposed
   * - 2023.1 Antelope
     - Reproposed
   * - 2023.2 Bobcat
     - Reproposed
   * - 2024.1 Caracal
     - Reproposed
   * - 2024.2 Dalmatian
     - Reproposed
