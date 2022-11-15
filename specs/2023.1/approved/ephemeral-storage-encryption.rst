..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Flavour and Image defined ephemeral storage encryption
======================================================

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

Problem description
===================

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
---------

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

Proposed change
===============

To enable this new flavor extra specs, image properties and host configurables
will be introduced. These will control when and how ephemeral storage
encryption at rest is enabled for an instance.

.. note::

   The following ``hw_ephemeral_encryption`` image properties do not relate to
   if an image is encrypted at rest within the Glance service. They only relate
   to how ephemeral storage will be encrypted at rest when used by a
   provisioned instance within Nova.

   Separate image properties have been documented in the
   `Glance image encryption`_ and `Cinder image encryption`_ specs to cover
   how images can be encrypted at rest within Glance.

Allow ephemeral encryption to be configured by flavor, image or config
----------------------------------------------------------------------

To enable ephemeral encryption per instance the following boolean based flavor
extra spec and image property will be introduced:

* ``hw:ephemeral_encryption``
* ``hw_ephemeral_encryption``

The above will enable ephemeral storage encryption for an instance but does not
control the encryption format used or the associated options. For this the
following flavor extra specs, image properties and configurables will be
introduced.

The encryption format used will be controlled by the following flavor extra
specs and image properties:

* ``hw:ephemeral_encryption_format``
* ``hw_ephemeral_encryption_format``

When neither of the above are provided but ephemeral encryption is still
requested an additional host configurable will be used to provide a default
format per compute, this will initially default to ``luks``:

* ``[ephemeral_storage_encryption]/default_format``

This could lead to requests against different clouds resulting in a different
ephemeral encryption format being used but as this is transparent to the end
user from within the instance it shouldn't have any real impact.

The format will be provided as a string that maps to a
``BlockDeviceEncryptionFormatTypeField`` oslo.versionedobjects field value:

* ``plain`` for the plain dm-crypt format
* ``luks``  for the LUKSv1 format

BlockDeviceMapping changes
--------------------------

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

    The ``encryption_options`` field will be unused and not exposed to end
    users initially because of the security and upgrade implications around it.
    For the first pass, sensible defaults for the cipher algorithm, cipher
    mode, and initialization vector generator algorithm will be hard-coded
    instead.

    Encryption options could be exposed to end users in the future when a
    proper design which addresses security and handles all upgrade scenarios is
    developed.

Populate ephemeral encryption BlockDeviceMapping attributes during build
------------------------------------------------------------------------

When launching an instance with ephemeral encryption requested via either the
image or flavor the ``BlockDeviceMapping.encrypted`` attribute will be set to
``True`` for each ``BlockDeviceMapping`` record with a ``destination_type``
value of ``local``. This will happen after the original API BDM dicts have been
transformed into objects within the Compute API but before scheduling the
instance(s).

The ``encryption_format`` attribute will also take its' value from the image or
flavor if provided. Any differences or conflicts between the image and flavor
for this will raise a ``409 Conflict`` error being raised by the API.

Use ``COMPUTE_EPHEMERAL_ENCRYPTION`` compatibility traits
---------------------------------------------------------

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
----------------------------------------------------

A new pre-filter will be introduced that adds the above traits as required to
the request spec when the aforementioned image properties or flavor extra specs
are provided. As outlined above this will always include the
``COMPUTE_EPHEMERAL_ENCRYPTION`` trait when ephemeral encryption has been
requested and may optionally include one of the format specific traits if a
format is included in the request.

Expose ephemeral encryption attributes via block_device_info
------------------------------------------------------------

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
----------------------------------------------------------------

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

Block resize between flavors with different hw:ephemeral_encryption settings
----------------------------------------------------------------------------

Ephemeral data is expected to persist through a resize and as such any resize
between flavors that differed in their configuration of ephemeral encryption
(one enabled, another disabled or formats etc) would cause us to convert this
data in place. This isn't trivial and so for this initial implementation
resizing between flavors that differ will be blocked.

Provide a migration path from the legacy implementation
-------------------------------------------------------

New ``nova-manage`` and ``nova-status`` commands will be introduced to migrate
any instances using the legacy libvirt virt driver implementation ahead of the
removal of this in a future release.

The ``nova-manage`` command will ensure that any existing instances with
``ephemeral_key_uuid`` set will have their associated ``BlockDeviceMapping``
records updated to reference said secret key, the ``plain`` encryption format
and configured options on the host before clearing ``ephemeral_key_uuid``.

Additionally the libvirt virt driver will also attempt to migrate instances
with ``ephemeral_key_uuid`` set during spawn. This should allow at least some
of the instances to be moved during the W release ahead of X.

The ``nova-status`` command will simply report on the existence of any
instances with ``ephemeral_key_uuid`` set that do not have the corresponding
``BlockDeviceMapping`` attributes enabled etc.

Deprecate the now legacy implementation
---------------------------------------

The legacy implementation within the libvirt virt driver will be deprecated for
removal in a future release once the ability to migrate is in place.

Alternatives
------------

Continue to use the transparent host configurables and expand support to other
encryption formats such as ``LUKS``.

Data model impact
-----------------

See above for the various flavor extra spec, image property,
``BlockDeviceMapping`` and ``DriverBlockDevice`` object changes.

REST API impact
---------------

* Flavor extra specs and image property validation will be introduced for the
  any ephemeral encryption provided options.

* Attempts to resize between flavors that differ in their ephemeral encryption
  options will be rejected.

* Attempts to rebuild between images that differ in their ephemeral encryption
  options will be allowed.

* The metadata API will be changed to allow users to determine if their
  ephemeral storage is encrypted as discussed above.

Security impact
---------------

This should hopefully be positive given the unique secret per disk and user
visible choice regarding how their ephemeral storage is encrypted at rest.

Additionally this should allow additional virt drivers to support ephemeral
storage encryption while also allowing the libvirt virt driver to increase
coverage of the feature across more imagebackends such as qcow2 and rbd.

Notifications impact
--------------------

N/A

Other end user impact
---------------------

Users will now need to opt-in to ephemeral storage encryption being used by
their instances through their choice of image or flavors.

Performance Impact
------------------

The additional pre-filter will add a small amount of overhead when scheduling
instances but this should fail fast if ephemeral encryption is not requested
through the image or flavor.

The performance impact of increased use of ephemeral storage encryption by
instances is left to be discussed in the virt driver specific specs as this
will vary between hypervisors.

Other deployer impact
---------------------

N/A

Developer impact
----------------

Virt driver developers will be able to indicate support for specific ephemeral
storage encryption formats using the newly introduced compute compatibility
traits.

Upgrade impact
--------------

The compute traits should ensure that requests to schedule instances using
ephemeral storage encryption with mixed computes (N-1 and N) will work during a
rolling upgrade.

As discussed earlier in the spec future upgrades will need to provide a path
for existing ephemeral storage encryption users to migrate from the legacy
implementation. This should be trivial but may require an additional grenade
based job in CI during the W cycle to prove out the migration path.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    melwitt

Other contributors:
    lyarwood

Feature Liaison
---------------

Feature liaison:
    melwitt

Work Items
----------

* Introduce ``hw_ephemeral_encryption*`` image properties and
  ``hw:ephemeral_encryption`` flavor extra specs.

* Introduce a new ``encrypted``. ``encryption_secret_uuid``,
  ``encryption_format`` and ``encryption_options`` attributes to the
  BlockDeviceMapping Object.

* Wire up the new ``BlockDeviceMapping`` object attributes through the
  ``Driver*BlockDevice`` layer and ``block_device_info`` dict.

* Report ephemeral storage encryption through the metadata API.

* Introduce new ``nova-manage`` and ``nova-status`` commands to allow existing
  users to migrate to this new implementation. This should however be blocked
  outside of testing until a virt driver implementation is landed.

* Validate all of the above in functional tests ahead of any virt driver
  implementation landing.

Dependencies
============

None

Testing
=======

At present without a virt driver implementation this will be tested entirely
within our unit and functional test suites.

Once a virt driver implementation is available additional integration tests in
Tempest and whitebox tests can be written.

Testing of the migration path from the legacy implementation will require an
additional grenade job but this will require the libvirt virt driver
implementation to be completed first.

Documentation Impact
====================

* The new host configurables, flavor extra specs and image properties should be
  documented.

* New user documentation should be written covering the overall use of the
  feature from a Nova point of view.

* Reference documentation around `BlockDeviceMapping` objects etc should be
  updated to make note of the new encryption attributes.

References
==========

.. _`Glance image encryption`: https://specs.openstack.org/openstack/glance-specs/specs/victoria/approved/glance/image-encryption.html
.. _`Cinder image encryption`: https://specs.openstack.org/openstack/cinder-specs/specs/wallaby/image-encryption.html
.. _`encrypted volume types`: https://docs.openstack.org/cinder/latest/configuration/block-storage/volume-encryption.html#create-an-encrypted-volume-type
.. _`libvirt virt driver`: https://libvirt.org/formatstorageencryption.html#StorageEncryptionLuks

History
=======

Optional section intended to be used each time the spec is updated to describe
new design, API or any database schema updated. Useful to let reader understand
what's happened along the time.

.. list-table:: Revisions
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
