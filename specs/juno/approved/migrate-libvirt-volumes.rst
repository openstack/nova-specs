..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================================
Use Libvirt Storage Pool Methods to Migrate Libvirt Volumes
===========================================================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/migrate-libvirt-volumes

Currently, the libvirt driver uses SSH (rsync or scp) to do cold migrations
and resizes on non-shared storage.  This requires SSH permissions between
compute nodes, which is problematic for a number of reasons.  Instead we can
use the methods built in to libvirt's storage pool API to do migrations.

NOTE: this proposal requires
`Use libvirt storage pools`_
(`Gerrit Spec Review <https://review.openstack.org/#/c/86947>`_).

Problem description
===================

The primary issue is that, currently, the Nova libvirt driver requires
SSH access between compute nodes to perform cold migrations and resizes on
non-shared storage.  This presents several issues:

* From a security perspective, providing SSH access between compute nodes
  is sub-optimal.  Giving compute nodes SSH access could allow a compromised
  node to compromise other nodes and potentially inflict harm on a cloud.

* From a setup perspective, it adds several extra steps to a setup:
  System administrators, or their setup tools, must generate a keypair
  for each compute node, and upload the public key to each of the other
  compute nodes.

Proposed change
===============

As specified in blueprint mentioned above, Nova's disk images would be placed
in a libvirt storage pool.  At migration time, a new volume would be created in
the destination node's storage pool, and the methods virStorageVolDowload and
virStorageVolUpload would be used to stream the contents of the disk between
compute nodes
(http://libvirt.org/html/libvirt-libvirt.html#virStorageVolUpload).

In order to ensure secure migrations, libvirt should be configured to use one
of the various forms of authentication and encryption that it supports, such as
Kerberos (via SASL -- http://libvirt.org/auth.html) or TLS client certificates
(http://libvirt.org/remote.html#Remote_libvirtd_configuration).

Note that this would only apply to setups using the new image backend
described in the previous blueprint; setups using the "legacy" image
backends would continue to use the SSH method until the "legacy" image
backends are removed.

Alternatives
------------

* Requiring shared storage for cold migrations and resizes: there are many
  OpenStack users who would like to be able to perform cold migrations and
  resizes without having shared storage.

* Just setting up SSH keys between compute nodes: see the problem description

* Temporarily provisioning SSH keys for the duration of the migration:
  While this somewhat mitigates the security issue and remove the extra setup
  steps, it still provides a window where the compute nodes are vulnerable.
  It would be much harder to secure, and would require having Nova be able
  to securely generate SSH keys.

* Using an rsync daemon: People seemed to be averse to requiring an rsync
  daemon.  Additionally, rsync daemon connections are not encryptable out
  of the box, although they can be run over stunnel.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

While this change does require two compute nodes' libvirt daemons to connect
to each other, such a process is already done by live migration.  While the
disks would no longer be encrypted by SSH while transfering, system
administrators could simply secure the libvirt connections instead
(http://libvirt.org/auth.html).  Libvirt supports TLS for encryption with x509
client certificates for authentication, as well as SASL for GSSAPI/Kerberos
encryption and authentication.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

There are a couple potential performance issues:

* Rsync compresses compress the contents to be transfered, but AFAIK libvirt
  does not (although this is being worked on in conjunction with the libvirt
  developers).  This could result in more data being transfered over
  the network.

* The actually streaming process would be using python as an intermediary
  (e.g. :code:`data = stream1.recv(1024*64); stream2.send(data)`, although
  the actual code would properly support async IO, detection of partial sends,
  etc).  While this would be less performant than having C code which would do
  the transfer, I suspect there are ways in which we could optimize the code.

Other deployer impact
---------------------

In order for the new method to work, deployers would have to enable the libvirt
daemon on each compute node to listen for remote libvirt connections (if live
migrations are enabled, this has already been done).  Such connections must be
secured as noted in `Security Impact`_.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
    sross-7

Other contributors:
    None

Work Items
----------

1. Implement the virStorageVolUpload/virStorageVolDownload code in the
   :code:`migrate_disk_and_power_off` method, replacing the existing calls
   to :code:`libvirt_utils.copy_image`.

2. Follow Up: remove the instances of SSH that create the instance directory
   and detect shared storage.  These could easily be done in a pre-migration
   method, similarly to how live-migration works currently.


Dependencies
============

`Use libvirt storage pools`_
(`Gerrit spec review <https://review.openstack.org/#/c/86947>`_)

.. _Use libvirt storage pools:
   https://blueprints.launchpad.net/nova/+spec/use-libvirt-storage-pools

Testing
=======

Since this only changes how migration works under the hood, existing migration
tests should be sufficient for the most part.


Documentation Impact
====================

For the OpenStack Security Guide, we should document that SSH keys are no
longer required between compute nodes, as well as provide instructions for
securing remove libvirtd connections.

In the Compute Admin Guide, we should provide instructions for how to enable
remote libvirtd connections (as required for libvirt live migration), as well
as noting that these connections need to be secured, as per the Security Guide.

Since much of this documentation also applies to libvirt live migrations, it
may be beneficial to place the instructions in a "general" section and link
to it from both the libvirt cold migrations and libvirt live migrations
documentation.


References
==========

* http://libvirt.org/html/libvirt-libvirt.html#virStorageVolUpload

* http://libvirt.org/auth.html)

* http://libvirt.org/remote.html#Remote_libvirtd_configuration
