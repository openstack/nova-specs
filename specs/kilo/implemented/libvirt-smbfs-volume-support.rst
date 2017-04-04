..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
Libvirt: Support for attaching volumes via SMB
==============================================

https://blueprints.launchpad.net/nova/+spec/libvirt-smbfs-volume-support

Currently, there are Libvirt volume drivers that support network-attached
file systems such as Gluster of NFS. The purpose of this blueprint is adding
support for attaching volumes hosted on a SMB share.

Problem description
===================

SMB is another widely used protocol, especially in the Microsoft world. Its
simplicity along with the big improvements that were introduced in SMB 3
make this type of volume backend a very good alternative.

SMB 3 brings features such as transparent failover, multichanneling using
multiple NICs, encrypted communication, and RDMA. Newer versions of Samba
are getting better support for the SMB 3 features, as well as supporting
Active Directory membership.

Use Cases
----------

Deployer will be able to attach block storage exported in the form of virtual
disks on SMB shares to instances.

Project Priority
-----------------

None


Proposed change
===============

A new volume driver will be added in order to support attaching volumes
hosted on SMB shares. The volume driver will have a similar worflow with
the NFS volume driver.

The SMB volume driver will mount the SMB share on which a volume is hosted
using credentials and other flags specified in the volume connection info.

This feature will be backwards compatible, supporting older versions of SMB
for simple tasks. It will support using any type of SMB share, including:

- from Scale-Out file servers to basic Windows shares;

- Linux SMB shares using Samba;

- vendor specific hardware exporting SMB shares.

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

The share credentials will be parsed in the volume connection info and used
when mounting a SMB share.

Also, the driver will support Active Directory integration (as long as the
Samba version supports it) so that it will be able to use AD credentials.

Note that as SAMBA does not support SELinux labelling, in order to be able
to boot from a volume hosted on a SMB share, the virt_use_samba SELinux
option will have to be enabled. This has security implications, as there
will no longer be any security isolation between VM disk images.

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

The deployer will be able to configure the path where the SMB shares will be
mounted, as well as setting mount flags.

Also, the Libvirt-qemu uid and gid will have to be specified as mount flags
in order to support attaching volumes because of Libvirt trying to change
the owner of the volume.

In order to support SMB3 and AD integration, Samba 4.0 or later is required.
Note that any version of Samba is supported by this driver but as older
versions don't support AD integration, you won't be able to use AD based
authentication. Also, in this case you must make sure that the SMB server you
are trying to access has no restrictions on the SMB protocol version, being
able to fall back to an older version.

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

Add support for mounting SMB shares.

Provide support for local shares.

Dependencies
============

None

Testing
=======

This feature should be tested using one of the SMB Cinder Volume drivers
already available. The existing Tempest tests along with the according unit
tests should be enough for the moment in order to test this.

While a CI is being considered, for the moment Tempest tests will be run
periodically for this scenario.

Documentation Impact
====================

Using the SMB backend will be documented.

References
==========

Cinder SMB Driver blueprint:
https://blueprints.launchpad.net/cinder/+spec/smbfs-volume-driver

