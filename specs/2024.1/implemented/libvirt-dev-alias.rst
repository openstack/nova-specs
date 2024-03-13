..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Move to using Libvirt device aliases
====================================

https://blueprints.launchpad.net/nova/+spec/libvirt-dev-alias

Currently we identify devices in Libvirt guest XML by a variety of methods,
which differs based on the device type (at least). Libvirt now provides a
device alias mechanism by which we can tie virtual guest devices to an
identifier we can use to look them up in a stable and generic way. Nova
should move to using that, which will increase consistency, decrease some
complexity, and also work around some issues with our current strategy.

Problem description
===================

Nova currently looks up guest devices in XML for attach/detach and other
modifications using a variety of methods. For example, disk devices use
the ``serial`` property to identify them uniquely. However, libvirt and
qemu do not support setting this property on all disk device types, which
means Nova cannot use that to look up disk devices in a generic way. Further,
if we have multiple network interfaces with the same MAC address, using that
as a unique identifier is not sufficient.

Example volume attachment::

    <disk type='block' device='disk'>
      <driver name='qemu' type='raw' cache='none' io='native'/>
      <source dev='/dev/sda' index='5'/>
      <backingStore/>
      <target dev='vdb' bus='virtio'/>
      <serial>ada5af06-300e-4d07-931d-3cc2bff8a8a9</serial>
      <alias name='virtio-disk1'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x0'/>
    </disk>

Use Cases
---------

As a developer, I want Nova to be able to manage libvirt guest devices in a
stable and consistent way.

As a deployer, I want Nova to support things like SCSI LUN passthrough, which
does not support setting the device serial in libvirt.

Proposed change
===============

Nova's libvirt driver should move to using the device alias mechanism
[1]_ for identifying all types of devices that are attach- or
detach-able. For devices like volumes and network interfaces, the
volume or port UUID should be used.  For other devices, some other
stable identifier that correlates to something in Nova or another
service's database is required. Libvirt has specific requirements for
the format of the alias, which must be followed. However, for most
devices that use a UUID as the primary identifier, we should be able
to embed that within the alias.

This is what the above disk example would look like with a
nova-specified alias::

    <disk type='block' device='disk'>
      <driver name='qemu' type='raw' cache='none' io='native'/>
      <source dev='/dev/sda' index='5'/>
      <backingStore/>
      <target dev='vdb' bus='virtio'/>
      <serial>ada5af06-300e-4d07-931d-3cc2bff8a8a9</serial>
      <alias name='ua-ada5af06-300e-4d07-931d-3cc2bff8a8a9'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x0'/>
    </disk>

Alternatives
------------

We could keep what we have and continue to not support disk devices that do not
support using ``serial``.

We could maintain our own mapping in our database for those device types.

Data model impact
-----------------

Nova's own data model is not affected by this and this is limited to
nova-compute and the libvirt driver. However, the libvirt XML data that we
currently maintain will need to change (and existing instances migrated) to
set the device aliases accordingly.

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

End users can currently request SCSI LUN-based disk device mapping, but it does
not work because we are unable to specify the device serial in that
configuration. After this change, that existing mechanism will begin to work.

Performance Impact
------------------

No major performance impact to Nova itself, although looking up
devices by alias will be easier and less computationally
intense. Further a detach-by-alias routine [2]_ is provided by
libvirt which may be significantly easier than what we currently need
to do by generating and providing an XML blob for detach.

Other deployer impact
---------------------

None.

Developer impact
----------------

The libvirt driver will ultimately be simpler after this change.

Upgrade impact
--------------

The only upgrade impact comes from migrating existing instance XML documents
to specify the device alias. Because we may be migrating instances to/from
older nodes, we should retain compatibility with alias-less XMLs for some time
to come.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dansmith

Other contributors:
  - kashyap
  - sean-k-mooney

Feature Liaison
---------------

dansmith

Work Items
----------

- Enable setting and parsing the device alias on disk, interface, and pci
  devices
- Actually set those device aliases in the various parts of the driver that
  create those configs
- Make the code that looks up devices by device-specific identifiers prefer the
  alias and fall back to the old way
- Migrate existing instance XMLs on startup when device aliases are missing

Dependencies
============

* Libvirt 3.9.0: https://libvirt.org/formatdomain.html#devices

Testing
=======

Existing devstack jobs should provide sufficient coverage other than the unit
and functional coverage that will be added. Potentially enabling (and using)
the LUN passthrough attachment mechanism would be beneficial, but that is
somewhat beyond the scope of this effort which is just changing the enumeration
behavior.

Documentation Impact
====================

There really is not much in the way of documentation impact because this
should be transparent to the operators and users.

References
==========

.. [1] Libvirt's device XML specification: https://libvirt.org/formatdomain.html#devices
.. [2] Libvirt's detach-by-alias function: https://libvirt.org/html/libvirt-libvirt-domain.html#virDomainDetachDeviceAlias

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2024.1
     - Introduced
