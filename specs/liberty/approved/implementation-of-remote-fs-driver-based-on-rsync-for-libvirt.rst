..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================================
Implementation of remote FS driver based on rsync for libvirt
===============================================================

https://blueprints.launchpad.net/nova/+spec/remote-fs-driver

libvirt cannot use RPC to copy files over network to/from other compute nodes.
That's why libvirt uses additional interface to communicate with other compute
nodes. Usage of fewer tools for communication between compute nodes can improve
security, ease of testing and deployment and give better flexibility.
Right now libvirt driver uses ssh and rsync commands for following operations:
* creation directory on remote host,
* creation file on remote host,
* removing file from remote host,
* copying file to remote host.
Target of this BP is implementation of two libvirt remote FS drivers: `ssh` and
`rsync` drivers. Each of these drivers will implement whole set of operation
needed by libvirt driver. `ssh` driver will use ssh and scp commands and
`rsync` driver will use rsync command only.


Problem description
===================

The current libvirt driver uses the following commands for executing remote
filesystem operations:
* ssh touch,
* ssh mkdir,
* ssh rm,
* scp,
* rsync.
This fact forces us to use an additional shell and this can cause security
risks. We can not avoid shell usage because copying files over network requires
a shell. It is possible to decrease the interaction between nodes by using ssh
commands or rsync commands only. Such separation can allow us to decrease
number of opened ports on node. Also using only rsync/scp commands can allow
us to use secure shells like rssh.

Use Cases
----------

The cloud operator wishes to reduce the number of commands used and the number
of ports opened by the  nova-compute daemon when migrating workloads between
compute nodes in order to reduce attack vectors.

Project Priority
-----------------

None.

Proposed change
===============

To achieve these goals abstract class 'RemoteFilesystem' will be added in
nova/virt/libvirt/remotefs.py. This class will contain operations needed for
libvirt to communicate with other nodes perform filesystem operations on those
nodes. This abstract class will be implemented in SshRemoteFilesystem and
RsyncRemoteFilesystem classes.
Class SshRemoteFilesystem will use ssh and scp tools only(scp uses ssh for data
transfer, and it uses the same authentication and provides the same security as
ssh).
Additional remote FS driver will be implemented in RsyncRemoteFilesystem class.
This class will use rsync command only.
Configuration option 'remote_filesystem_transport' will be added with default
value 'ssh' and 'choices ssh', 'rsync'. Depending on option value corresponding
class will be instantiated.

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

These improvements allow us to decrease number of used ports on compute node.
Also it allows us to use restricted shell for providing limited access to a
host like 'rssh'.

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

To achieve security benefits some kind of restricted shell must be installed
on compute nodes. New shell should be used for nova user.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee: mhorban@mirantis.com

Work Items
----------

* Implementation of ssh remote FS driver for libvirt.
* Implementation of rsync remote FS driver for libvirt.
* Addind configuration option to choose remote FS driver.


Dependencies
============

None.


Testing
=======

tempest test for migration instances will be added.


Documentation Impact
====================

Adding new option 'remote_filesystem_transport' to configure method of compute
node communication.


References
==========
