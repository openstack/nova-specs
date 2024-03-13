..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
Mediated device live migration with libvirt
===========================================

https://blueprints.launchpad.net/nova/+spec/libvirt-mdev-live-migrate

Starting with libvirt-8.6.0, QEMU-8.1.0 and Linux kernel 5.18.0, guests using
mediated devices can be live migrated by using a target mediated device using
the same mediated device type (and we don't need to unplug/plug the mdevs).
Now, we need to support this for Nova, which means that Nova should provide
a target mediated device UUID (that exists) to the source compute service by
the pre-live-migrating call so the target XML created by the source would use
it.


Problem description
===================

For the moment, this is not possible to live-migrate an instance if it uses a
mediated device as the target wouldn't create it. You can only for the moment
cold-migrate the instance or do other move operations like shelve.
Fortunately, libvirt 8.5.0 now supports to live-migrate a guest by using a
target mediated device uuid in the target XML so we want to directly support
this in Nova.

Use Cases
---------

As an operator, I want to move my instance using a vGPU to another host without
the user being aware of it.

As an operator, I want to make sure I will only live-migrate by using the same
mediated device type between the source and the target.

Proposed change
===============

In order to succesfully live-migrate a guest with libvirt, you need to modify
the target guest XML to use another mediated device using the same mdev
(mediated device) type.
In order to do it, we propose the following workflow :

First, during the conductor compatibility checks, we will verify the types
compatibility on the destination and we will claim for a specific list of
target mediated devices (either to be created or just kept reserved) this way :

- ``check_can_live_migrate_source()`` (run on the source) will check the
  libvirt version of the source and fail by raising a
  ``MigrationPreCheckError`` if the version if below the minimum required (see
  `Dependencies`_) and only if the instance has mediated devices. It will also
  check the ``LibvirtLiveMigrateData`` version returned by the destination and
  will raise a ``MigrationPreCheckError`` exception if older than the one
  supporting the new fields (see both `Upgrade Impact`_ and
  `Data model impact`_).
  Eventually, it will return the list of number of mdevs with their types back
  to the target in the ``LibvirtLiveMigrateData`` object.

- driver's ``post_claim_migrate_data()`` will first check based on the
  ``LibvirtLiveMigrateData`` object whether the libvirt version is below the
  minimum required and then check whether those mdev types are compatible with
  the types the target supports and will raise a ``MigrationPreCheckError`` if
  not. If successful, it will pick N (N being the requested number) of the
  available mediated resources (either by creating new mdevs or taking existing
  ones), based on the list that was passed thru ``LibvirtLiveMigrateData``, and
  will persist that list of target mediated devices in some internal dictionary
  field of the ``LibvirtDriver`` instance, keyed by the instance UUID. We will
  also pass those mdev uuids in the ``LibvirtLiveMigrateData`` object that we
  return over the wire to the source compute (we will call it later `migrate
  data object`).

.. note:: the current spec proposal is to use the existing NUMA-live-migration
          related method called `post_claim_migrate_data()`__ but we could
          create a specific new virt driver API method for this usage. This
          will be discussed at implementation stage.

.. __: https://github.com/openstack/nova/blob/45e2349408dd3b385217066a3c5a4c29d7bdd3a0/nova/virt/libvirt/driver.py#L9749

Later, once the source host starts the live-migration, we will update
the guest XML information with those mediated device UUIDs this way :

- in source's driver ``_live_migration_operation()`` we lookup the migrate data
  object we got and we update the target guest XML in
  ``get_updated_guest_xml()`` by getting those mediated device UUIDs from the
  migrate data object.

- in destination's driver ``post_live_migration_at_destination()``, we delete
  the mdevs tracked in the internal dictionary field of the ``LibvirtDriver``
  instance by getting them from the dictionary which is keyed by the instance
  UUID.

In case of any live migration abort or exception, the residue we only need to
clean up is basically the list of claimed mediated devices for the migration
that are set in the dictionary field of the ``LibvirtDriver`` instance.
Accordingly, we propose to delete those records this way :

- if the exception occurred during pre-livemigration, it eventually calls on
  destination ``rollback_live_migration_at_destination()`` depending on
  ``_live_migration_cleanup_flags()`` result. We will modify that verification
  method to lookup whether we have mediated device UUIDs in the migrate data
  object. Then, ``rollback_live_migration_at_destination()`` will again look at
  the dictionary to know which mediated devices to remove from the internal
  dictionary in the ``LibvirtDriver``.

- if the exception happened during the live-migration (or if the operator asked
  to abort it), then it eventually calls ``_rollback_live_migration()`` which
  also calls ``rollback_live_migration_at_destination()`` like above, so it
  would also remove the mdevs from the ``LibvirtDriver`` dictionary field.

As a side note, the `current method`__ we have for knowing which mediated
devices are used by instances will be modified to also take in account the list
of mediated devices that are currently set in internal directory field of the
LibvirtDriver we'll be using for tracking which mdevs are claimed for
migrations.

.. __: https://github.com/openstack/nova/blob/b64ecb0cc776bd3eced674b0f879bb23c8a4b486/nova/virt/libvirt/driver.py#L8361-L8394

Alternatives
------------

Operators could continue to only do cold migrations or we could try to unplug
and then plug mediated devices during live-migration like we do at the moment
for SR-IOV VFs.


Data model impact
-----------------

While we won't describe the internal dictionary we would use in the
``LibvirtDriver`` class instance as this is just an implementation question, we
still need to explain which objects will be passed between computes RPC
services. As we said earlier, we need to augment the ``LibvirtLiveMigrateData``
object.

New fields will be added on that object (we can create a nested object if
people prefer):

* ``source_mdev_types: fields.DictOfStringsField()`` : dictionary where the key
  is a source mediated device UUID and the value is its mdev type.

* ``target_mdevs: fields.DictOfStringsField()`` : dictionary where the key is a
  mediated device UUID of the source and the value a mdev UUID of the target,
  implicitly matching the relationship between both for the live-migration.


REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

Operators wanting to use vGPU live-migration will need to support a recent
libvirt release, so they probably need to upgrade their OS. They will also need
to upgrade all their compute services, see `Upgrade Impact`_ for more details.

Developer impact
----------------

None.

Upgrade impact
--------------

Operators will need to make sure that the target computes are upgraded.
That said, given if the destination is not upgraded (and then doesn't support
live migration), then it would return a ``LibvirtLiveMigrateData`` object
with a previous version. The source will know that the target doesn't
support it and will accordingly raise ``MigrationPreCheckError`` (we detailed
that above in `Proposed change`_).


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sylvain-bauza

Other contributors:
  None

Feature Liaison
---------------

N/A

Work Items
----------

* add the ``LibvirtDriver`` internal dictionary
* augment the ``LibvirtLiveMigrateData`` object
* add the conductor checks
* add the live-migration changes

Dependencies
============

As said above, it requires :
- libvirt-8.6.0 and newer
- QEMU-8.1.0 and newer
- Linux kernel 5.18.0 and newer


Testing
=======

Unit and functional tests are a very bare minimum but we're actively chasing
the idea to use the `mtty kernel samples framework`__ as a way to do some
Tempest testing that's yet unwritten. We may need to build a custom kernel in
order to get the latest version of mtty that includes live-migration support.

.. __: https://www.kernel.org/doc/html/v5.8/driver-api/vfio-mediated-device.html#using-the-sample-code


Documentation Impact
====================

We'll augment the usual `virtual GPU documentation`__ with a section on how to
live-migrate and its requirements.

.. __: https://docs.openstack.org/nova/latest/admin/virtual-gpu.html

As a note, the specific proprietary nVidia `vfio-mdev` driver that provides
mediated device types and live-migration support currently has limitations and
doesn't support pausing a VM and autoconverge feature. Besides, live-migration
downtime is very depending on the hardware so we somehow need to document those
hardware-specific knobs in some abstract manner in our upstream docs, pointing
as much as we can to the vendor documentation if existing.


References
==========

* https://qemu.readthedocs.io/en/v8.1.0/devel/vfio-migration.html
* https://wiki.qemu.org/ChangeLog/8.1#VFIO
* https://lore.kernel.org/all/20220512233222.GH1343366@nvidia.com/T/
* (libvirt doc missing)

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2024.1 Caracal
     - Introduced
