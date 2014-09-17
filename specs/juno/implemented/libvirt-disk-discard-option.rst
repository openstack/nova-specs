..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Libvirt-Enable support discard option for disk device
======================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-disk-discard-option

Most SCSI devices have supported UNMAP command which is used to return unused
or freed blocks back to the storage. And SSD drive have a similar command
called "Trim" command.

This blueprint aims to support setting discard option for instance's disk.
If discard option is enabled, unused/freed blocks can be return back to the
storage device.

Qemu1.5 has supported setting discard option for the raw disk. In Qemu1.6,
qcow2 file supported discard option too.

Cinder support is out of scope for this spec. This spec only covers disks
managed by nova.

Problem description
===================

Thin provision volume
---------------------
When we write data to a thin provision volume, storage device will allocate
blocks to it and it will grow.
But without discard option supported, the blocks will not be freed to the
storage device even if we deleted the data in the volume. The result is the
thin volume can grow, but can't shrink.
With discard option supported, when user deleted the data in the volume,
the blocks will be freed to the storage device. The volume will shrink.

It's useful for both ephemeral volume and cinder volume.

SSD backed volume
--------------------
Freeing the unused blocks to the SSD storage is useful to improving the
performance and prolonging the lifetime of SSD.

Proposed change
===============

Add support for the deployer to specify the discard option in the nova.conf by
"hw_disk_discard".

There are two available values for "hw_disk_discard" now::

  "unmap" : Discard requests("trim" or "unmap") are passed to the filesystem.
  "ignore": Discard requests("trim" or "unmap") are ignored and aren't passed
  to the filesystem.

For example::

  hw_disk_discard=unmap    #enable discard
  hw_disk_discard=ignore   #disable discard, by default

For an instance running on a host which has the discard option in nova.conf,
nova will produce the XML with a discard option when the nova managed disk
is attached.

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
Discard option maybe cause performance degradation and fragmentation.
But for the storage based on SSD, discard option is good for the performance.

The users have control over this behaviour in the guest os if they don't want
it. They can use the mount parameter or the command tools to control the
discard behaviour.

Other deployer impact
---------------------
Initially, only the libvirt driver will support this function, and
only with qemu/kvm as the hypervisor.

A serious consideration is needed before enabling discard option.
With discard option enabled, the freed blocks of the thin provision volume
will be return to the storage and can be reused. But it also maybe cause
performance degradation and fragments.
So it's reasonable to enable the discard option only when you use the thin
provision volume and the storage are UNMAP/TRIM-capable. For example the SSD,
the disk-arrays or other distributed storage which supports the UNMAP/TRIM.

Developer impact
----------------
None


Implementation
==============

Assignee(s)
-----------
boh.ricky

Work Items
----------

* Libvirt driver will create a discard option for a disk device which the
  instance flavor has discard option.

Dependencies
============
Libvirt(1.0.6) Qemu1.5(raw format) Qemu1.6(qcow2 format)

Testing
=======
None

Documentation Impact
====================

The document should be modified to reflect this new feature.

References
==========
None
