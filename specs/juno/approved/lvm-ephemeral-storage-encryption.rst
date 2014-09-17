..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Ephemeral storage encryption for LVM backend
============================================

https://blueprints.launchpad.net/nova/+spec/lvm-ephemeral-storage-encryption

The proposed feature will provide data-at-rest security for LVM backed,
libvirt managed ephemeral storage devices attached to a VM instance.


Problem description
===================

The current implementation of LVM ephemeral storage leaves user data vulnerable
following instance shutdown, through disk block reuse (if data is not
securely erased), improper storage media disposal and physical facility
compromise.

For example, if a compute node goes down without properly disposing of the
active instances, when it is restarted, the disk blocks that held pre-reboot
instances' data will be reallocated to new instances.  Since LVM storage is not
sanitized before allocation this, in principle, permits recovery of other
users' data.


Proposed change
===============

User data can be protected against inadvertant disclosure by encrypting
ephemeral storage disks with a unique key, accessible only via a secure key
manager (most likely Barbican, currently in incubation) with proper
credentials. The feature will be labeled optional until the status of Barbican
key manager is finalized.

This feature is part of a larger effort to add ephemeral storage encryption to
OpenStack.


Alternatives
------------

It is unlikely there is another solution that would cover all the cases such
unexpected compute node events, preventing proper instance shutdown,
improper storage media disposal, etc., covered by ephemeral storage encryption.

For example, ephemeral disks could be sanitized before being attached to
instances to prevent disclosure due to block storage reuse.  However, this
would not protect users' data against improper storage media disposal.
Moreover, data sanitization is expensive since the entire ephemeral disk,
which can be sizeable, must be wiped.

Data model impact
-----------------

All necessary data objects and database changes have already been made. See

* https://blueprints.launchpad.net/nova/+spec/encrypt-ephemeral-storage

* https://review.openstack.org/#/c/61544/

* https://review.openstack.org/#/c/60621/

REST API impact
---------------

None

Security impact
---------------

This feature will make LVM ephemeral storage more secure by providing
data-at-rest security for user data.

* A uniqe encryption key is created for each instance (or batch of
  instances in case of a batch launch) in
  compute.API._populate_instance_for_create() and stored securely using key
  manager (e.g., Barbican).

* The key is retrieved, using its uuid and the user's context, immediately
  before the ephemeral disk is created to minimize the exposure.

Potential security concerns:

* Command cryptsetup will be added to the rootwrap filter.

* User context will be passed to imagebackend.Lvm.create_image(),
  LibvirtDriver.create_swap() and LibvirtDriver.create_ephemeral() from
  LibvirtDriver._create_image()

Notifications impact
--------------------

None

Other end user impact
---------------------

Certain instance operations:

* instance rescue

may not be immediately supported.

Performance Impact
------------------

The optional encryption layer imposes a roughly 10% performance penalty
on ephemeral storage I/O performance, according to measurements performed
with the Phoronix test suite on a single-node DevStack cloud.

Other deployer impact
---------------------

* LVM ephemeral storage encryption is controlled by 3 options collected in the
  ephemeral_storage_encryption options group.  The name is deliberately generic
  since the same options could be used to control encryption for other
  backends.

  ephemeral_storage_encryption options group

  * enabled:Boolean -- enables/disables LVM ephemeral storage encryption;
                       default is False

  * cipher:String -- cipher-mode string to be passed to cryptsetup; the set of
                     cipher-mode combinations available depends on kernel
                     support; default is aes-xts-plain64

  * key_size:Integer -- encryption key length in bits; default is 512

  The default values have been chosen to provide a high level of
  confidentiality.  (Note that in XTS mode only half of the key bits are
  used for encryption key.)

* Encryption is implemented using the cryptsetup utility, which is available
  as a package on most Linux distributions.


Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Dan Genin <daniel.genin@jhuapl.edu>

Other contributors:
  None

Work Items
----------

Two of the three components comprising the feature:

* adding ephemeral storage encryption key uuid to Nova DB
  (https://review.openstack.org/#/c/61544/)

* dmcrypt module for interacting with cryptsetup
  (https://review.openstack.org/#/c/60621/)

have already merged in Icehouse.

The final remaining item is to actually add encryption to imagebackend.Lvm.

Dependencies
============

Depends on Barbican (https://review.openstack.org/#/c/94918/) for key
management.

Depends on cryptsetup being installed.


Testing
=======

We will work to implement Tempest tests for the feature. However, Tempest
testing will require Tempest support for LVM backed ephemeral storage as
well as Barbican for key management. These changes may take some time to
implement.

Documentation Impact
====================

Ephemeral storage encryption configuration options and its dependencies,
namely dmcrypt/cryptsetup and Barbican, will have to be documented.


References
==========

None
