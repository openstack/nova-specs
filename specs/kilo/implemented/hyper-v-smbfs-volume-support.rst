..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
Hyper-V: Support for attaching volumes via SMB
==============================================

https://blueprints.launchpad.net/nova/+spec/hyper-v-smbfs-volume-support

Currently, the Hyper-V driver allows attaching volumes only via iSCSI. The
purpose of this blueprint is adding support for attaching volumes hosted on
a SMB share.

Problem description
===================

For the moment, there are drivers which support distributed file systems such
as Gluster or NFS as volume backends. SMB is another widely used protocol,
especially in the Microsoft world.

Its simplicity along with the big improvements that were introduced in SMB 3
make this type of volume backend a very good alternative.

SMB 3 brings features such as transparent failover, multichanneling using
multiple NICs, encrypted communication, and RDMA. Note that in order
to use live migration, SMB 3 is required.

This feature will be backwards compatible, supporting older versions of SMB
for simple tasks. It will support using any type of SMB share, including:

- from Scale-Out file servers to basic Windows shares;

- Linux SMB shares using Samba;

- vendor specific hardware exporting SMB shares.

Use Cases
----------

Deployer will be able to attach to instances block storage volumes exported as
virtual disks on SMB shares.

Project Priority
-----------------

None


Proposed change
===============

A new volume driver will be added in order to support attaching volumes
hosted on SMB shares. The Hyper-V driver will be able to choose between the
volume drivers using the volume type stored in the connection info.

The SMB volume driver will mount the share on which a volume is hosted using
credentials specified in the volume connection info, then attach the volume
to a VM using its UNC path. This way, the Hyper-V driver will be able to
attach vhd or vhdx images hosted on SMB shares.

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

The credentials recieved in the volume connection_info will be used in
order to mount the according SMB share.

Note that the Hyper-V VMMS user account needs access to the remote image file
in order to be able to attach it to instances. As a best practice, the Cinder
and Nova nodes should be part of the same AD domain, using AD credentials
and giving the required permissions to Hyper-V VMMS.

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

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <lpetrut@cloudbasesolutions.com>

Other contributors:
  <gsamfira@cloudbasesolutions.com>

Work Items
----------

Add SMB Volume driver.

Adapt Hyper-V Driver in order to be able to use multiple volume drivers
according to volume types.

Adapt existing volume related operations such as lookups in order to support
disk resources stored on SMB shares.

Dependencies
============

None

Testing
=======

This feature should be tested along with the upcoming SMB Cinder driver.
CI testing will be performed by the Hyper-V CI.

Documentation Impact
====================

Using the SMB backend will be documented.

References
==========

Cinder SMB Driver blueprint:
https://blueprints.launchpad.net/cinder/+spec/smbfs-volume-driver
