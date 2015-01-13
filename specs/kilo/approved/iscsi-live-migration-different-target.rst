..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================
Support iSCSI live migration for different iSCSI target
=======================================================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/iscsi-live-migration-different-target

Currently, Nova premises a situation which iSCSI target is not changed
before and after live migration. Therefore, if destination node has
different iSCSI target, the live migration fails in current Nova's
specification. However, if each compute node uses same iSCSI target,
each compute node recognizes all volumes in the iSCSI target and this
is undesirable situation from the view point of security.

Therefore, this spec proposes to support live migration of instances with
Cinder volumes among compute nodes that need to log into different
iSCSI targets to access the volumes.

For your reference, if iSCSI storages have features to manage visibility
of LUNs for each initiator within one iSCSI target, using same iSCSI
target for each compute node is not a problem. But general iSCSI storages
don't have such kind features, therefore they need this feature to
support live migration.

Problem description
===================

In general, if multiple compute nodes use a same iSCSI target to export
volumes, each compute node recognizes all volumes in the target even if
some volumes are not attached to instances of a compute node.
This may cause slowdown of SCSI device scan if thousands of SCSI devices
are recognized on a compute node and also this is undesirable situation
from the view point of security.

On the other hand,

* Cinder LVM driver avoids this problem by creating unique iSCSI target
  for each volume.
* Some enterprise iSCSI storages has features to manage visibility of
  LUNs for each initiator within one iSCSI target.

But, generally storages have a limitation of a number of iSCSI target,
which is often less than maximum number of LUs.
In addition, there is a case that a storage does not have a feature
of visibility management of iSCSI target for multiple initiators.

In this case, by creating individual iSCSI target for each compute node and
managing visibility by connecting LUs to a corresponding iSCSI target
when the volumes is attached to instances on the node, we can avoid this
problem and utilize the storage capacity.

However, Nova currently premises a situation which iSCSI target is not
changed before and after live migration. Therefore, during live migration,
a source node pass a host device path which is created from the address of
iSCSI target portal, IQN, etc to destination node. This causes failure of
live migration if destination node has different iSCSI target.

In order to solve current problem, this spec proposes to support
of live migration for different iSCSI targets.

Use Cases
----------

Using this proposal, each compute node can utilize individual iSCSI target.
As a result, each compute node only recognizes volumes which are related to
a compute node. This can be reduce load of unnecessarily SCSI device scan,
udev high work load and decrease security risk.

Project Priority
-----------------

None.

Proposed change
===============

Following changes premise a result which each initiator returns
different iSCSI target IQN at initialize_connection() of Cinder
during live migration.

In libvirt driver,

(1) Store device path of block devices on destination host into
    pre_live_migration_data during pre_live_migration() .....[EX1]

(2) Check "serial" field of each disk in domain definition XML.
    Then, if the original "serial" and destination "serial" are same
    value, replace "source dev" in the XML using device paths from
    destination host .....[EX2]

    QEMU built-in iSCSI initiator(libiscsi) will be supported during
    Kilo phase. This proposal need to take account of both
    iscsi-initiator case and libiscsi case.

    * https://review.openstack.org/#/c/133048/

    If the initiator is libiscsi, replace "name", "host name" and "port"
    fields in the XML using res_data from destination host .....[EX3]

(3) Pass the new XML data to libvirt migrateToURI2 API.


[EX1]::

 res_data
  {'device_path': {u'58a84f6d-3f0c-4e19-a0af-eb657b790657':
    u'/dev/disk/by-path/ip-192.168.0.10:3260-iscsi-iqn.abc.org.67890.
    opst-lun-Z'},
   'graphics_listen_addrs': {'vnc': '127.0.0.1', 'spice': '127.0.0.1'}}


[EX2]

For iscsi-initiator::

  [Before]
  <disk type='block' device='disk'>
     <driver name='qemu' type='raw' cache='none'/>
     <source dev='/dev/disk/by-path/
                 ip-192.168.0.10:3260-iscsi-iqn.abc.org.12345.opst-lun-X'/>
     <target dev='vdb' bus='virtio'/>
       <serial>58a84f6d-3f0c-4e19-a0af-eb657b790657</serial>
       <address type='pci' domain='0x0' bus='0x0' slot='0x04' function='0x0'/>
  </disk>


  [After]
  <disk type='block' device='disk'>
     <driver name='qemu' type='raw' cache='none'/>
     <source dev='/dev/disk/by-path/
                 ip-192.168.0.10:3260-iscsi-iqn.abc.org.67890.opst-lun-Z'/>
     <target dev='vdb' bus='virtio'/>
       <serial>58a84f6d-3f0c-4e19-a0af-eb657b790657</serial>
       <address type='pci' domain='0x0' bus='0x0' slot='0x04' function='0x0'/>
   </disk>


[EX3]

For libiscsi::

  [Before]
  <disk type='network' device='disk'>
     <driver name='qemu' type='raw'/>
     <source protocol='iscsi' name='iqn.abc.org.12345.opst/X'>
       <host name='192.168.0.10' port='3260'/>
     </source>
     <serial>58a84f6d-3f0c-4e19-a0af-eb657b790657</serial>
     <target dev='vdb' bus='virtio'/>
  </disk>


  [After]
  <disk type='network' device='disk'>
     <driver name='qemu' type='raw'/>
     <source protocol='iscsi' name='iqn.abc.org.67890.opst/Z'>
       <host name='192.168.0.10' port='3260'/>
     </source>
     <serial>58a84f6d-3f0c-4e19-a0af-eb657b790657</serial>
     <target dev='vdb' bus='virtio'/>
  </disk>


Alternatives
------------

None.

Data model impact
-----------------

None.

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

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mtanino


Work Items
----------

These two patches will be posted.

1. Support iscsi-initiator

2. Support QEMU built-in iSCSI initiator(libiscsi)

Dependencies
============

None.

Testing
=======

- Unit tests should be added.

Documentation Impact
====================

None.

References
==========

None.
