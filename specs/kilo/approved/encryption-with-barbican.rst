..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Make key manager interface interoperable with Barbican
======================================================

URL to Launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/encryption-with-barbican

The volume encryption feature added in the Havana release currently can only
operate with a single key that is hardcoded in.  A much more flexible and
secure solution would be to generate and store keys in Barbican, a cohesive and
secure Linux-based key management system
https://github.com/cloudkeep/barbican/wiki, which is now in the OpenStack
incubation process.


Problem description
===================

Problem 1: The OpenStack Volume Encryption feature currently cannot provide its
designed level of security due to the absence of a key management service.
Only a placeholder is available now, which isn't sufficient for the volume
encryption feature to be used in an enterprise environment.  Keys cannot be
stored, and only one hard-coded key is presented for all volumes. The proposed
outcome would provide the ability to create and safely store dedicated keys for
individual users or tenants.

Problem 2: An ephemeral disk encryption feature supporting LVM was not accepted
into the Icehouse release due to the lack of a key manager. For security
reasons, since the disk is in close proximity to the virtual host, ephemeral
disk encryption must use a key that's safely stored outside of the virtual host
environment.

An enterprise-grade key manager is needed for both cases, and Barbican
(approved for incubation on 3/10/14) is becoming the default key manager that
is slated to support OpenStack volume encryption, ephemeral disk storage
encryption, and other potential security features.
https://wiki.openstack.org/wiki/Barbican/Incubation. In order for Barbican to
support these two storage encryption features, an interface between the
existing key manager interface (nova/keymgr/key_mgr.py) used for volume
encryption and the Barbican key manager needs to be developed.

Use Cases
---------

Users who wish to use the OpenStack Volume Encryption feature currently don't
have the ability to have encryption on a per-tenant basis.  It currently has
a single unchangable key.  By adding the option of using the Barbican Key
Manager, a separate key can be created and stored for each tenant. This makes
the feature much more secure.

Project Priority
----------------

N/A


Proposed change
===============

Create an interface that will call python-barbicanclient, allowing Barbican to
securely generate, store, and present encryption keys to Nova in support of the
volume encryption feature.  The adapter will be a modification of the present
key management abstraction layer in the volume encryption feature supporting
block storage encryption on Cinder and ephemeral disk encryption.

Alternatives
------------

Instead of implementing the existing key manager interface,
python-barbicanclient could be invoked directly, but the additional indirection
allows more extensibility if a different key manager needs to be integrated
later.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

Use of a bonafide key manager greatly improves the security posture of the
volume encryption and upcoming ephemeral disk encryption features.  When each
user or tenant use a unique key instead of a common key, and when it is stored
in a separate server, it will be much more difficult for an attacker to access
stored encrypted data owned by a user or group of collective users within a
tenant.

Though the wrapper will be handling encryption keys, the security risk is
considered minimal since the host must be trusted, and the wrapper is only
holding the key temporarily.


Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

The additional storage write and read time to initially query Barbican for the
encryption key should be negligible.

Other deployer impact
---------------------

Assuming that Barbican is the default key manager, then no impact.  If it's not
the default, then a configuration flag in Nova will need to be added.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  hadi-esiely-barrera

Other contributors:
  brianna-poulos
  bruce-benjamin

Work Items
----------

Develop simple translation of existing key manager interface methods (e.g.,
get_key) into the corresponding python-barbicanclient calls.

Dependencies
============

None


Testing
=======

Tempest testing should be performed to ensure that the wrapper works correctly.


Documentation Impact
====================

The use of Barbican as the default key manager for the storage encryption will
need to be documented.


References
==========

None

