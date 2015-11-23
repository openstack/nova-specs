..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================================
Use Libvirt Storage Pool Methods to Migrate Libvirt Volumes
===========================================================

https://blueprints.launchpad.net/nova/+spec/migrate-libvirt-volumes

Currently, the libvirt driver only uses SSH (rsync or scp) to do cold
migrations and resizes on non-shared storage.  This requires SSH
permissions between compute nodes, which is problematic for a number of
reasons.  Instead we can use the methods built in to libvirt's storage
pool API to do migrations.

NOTE: this proposal requires `Use libvirt storage pools`_
https://blueprints.launchpad.net/nova/+spec/use-libvirt-storage-pools

Problem description
===================

The primary issue is that, currently, the Nova libvirt driver requires
SSH access between compute nodes to perform cold migrations and resizes
on non-shared storage.  This presents several issues:

* From a security perspective, providing SSH access between compute nodes
  is sub-optimal.  Giving compute nodes SSH access could allow a compromised
  node to compromise other nodes and potentially inflict harm on a cloud.

* From a setup perspective, it adds several extra steps to a setup:
  System administrators, or their setup tools, configure libvirt to use
  a secure communication channel between source and target node.
  This could be the use of TLS for example.  They must also generate a
  keypair for each compute node, and upload the public key to each of
  the other compute nodes.

Use Cases
---------

Deployer: This allows the deployer to not have to set up SSH access between
compute nodes while still supporting non-shared-storage resizes and cold
migrations, as long as the deployer is using the new libvirt storage pools
image backend.

Proposed change
===============

The functionality in this blueprint would only be used when the deployer is
using the new libvirt storage pool image backend, and has enabled the
:code:`[libvirt]vol_upload_migration` option.

At migration time, a new volume would be created in the destination node's
storage pool, and the methods virStorageVolDownload and virStorageVolUpload
would be used to stream the contents of the disk between compute nodes
(http://libvirt.org/html/libvirt-libvirt-storage.html#virStorageVolUpload).

In order to ensure secure migrations, libvirt should be configured to use one
of the various forms of authentication and encryption that it supports, such as
Kerberos (via SASL -- http://libvirt.org/auth.html) or TLS client certificates
(http://libvirt.org/remote.html#Remote_libvirtd_configuration).

To enable migration of suspended instances virDomainSave() will be used to
save instance memory instead of virDomainManagedSave().  This will enable
control of the file location, so it could be created in a directory based
storage pool.  This will mean you can use the storage pool APIs to upload
and download that data during cold migration of suspended instances


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

* Rsync can compress the contents to be transfered, although nova does
  not use this option.  However, it does do efficient sparse handling
  by default.

* Libvirt does not do compression or handle sparse files efficiently.
  A libvirt bug has been filed to request better sparse handling
  https://bugzilla.redhat.com/show_bug.cgi?id=1282795

* In either case the use of compression is not recommended due to the
  impact on source node utilization.

* The current rsync implementation will remain the default until the
  libvirt performance issues are addressed.

Other deployer impact
---------------------

In order for the new method to work, deployers would have to enable the libvirt
daemon on each compute node to listen for remote libvirt connections (if live
migrations are enabled, this has already been done).  Such connections must be
secured as noted in `Security Impact`_.

Additionally the configuration option :code: `[libvirt]vol_upload_migration`
would need to be enabled.  This is especially important until we can guarantee
the performance is on par with the current SSH/rsync functionality (when
disabled, we would fall back to the current SSH/rsync-based functionality).

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
    paul-carlton2

Other contributors:
    None

Work Items
----------

1. Implement the virStorageVolUpload/virStorageVolDownload code in the
   :code:`migrate_disk_and_power_off` method, as an alternative to the existing
   calls to :code:`libvirt_utils.copy_image`.

2. Follow Up: remove the instances of SSH that are used to set up and tear down
   the migration (e.g. for shared storage detection).  These could easily be
   done in a manner similar to how live migration works (having
   pre_migrate_host and pre_migrate_dest methods, instead of SSHing).


Dependencies
============

`Use libvirt storage pools`_

.. _Use libvirt storage pools:
   https://blueprints.launchpad.net/nova/+spec/use-libvirt-storage-pools

Testing
=======

Since this only changes how migration works under the hood, existing migration
tests could simply be run again with the :code:`[libvirt]vol_upload_migration`
configuration option enabled on a setup where the libvirt storage pool image
backend is also in use.

Enable these code paths and work with the "bleeding edge" libvirt tests
which are being created to test.


Documentation Impact
====================

For the OpenStack Security Guide, we should note that the new functionality can
be used as an alternative to deploying SSH access between compute nodes,
instead of having to provision SSH keys for the compute nodes, as well as
provide instructions for securing remote libvirtd connections.

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

* http://libvirt.org/auth.html

* http://libvirt.org/remote.html#Remote_libvirtd_configuration
