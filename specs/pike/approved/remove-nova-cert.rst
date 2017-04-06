..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================
Remove nova-cert
===================

https://blueprints.launchpad.net/nova/+spec/remove-nova-cert

``nova-cert`` has been deprecated for some time and now can be removed
completely.

Problem description
===================

Because of the legacy requirements of building euca bundles which require
certificates, Nova has a very old and unmaintained "certificates" API. This
allows a user to use openssl on their Nova cluster to generate certificates
randomly instead of doing so locally. Private keys are returned during the POST
call, and the root certificate can be fetched later.

Behind the scenes this work is done by having a nova-cert worker. While it
is intended to be used as a fleet for entropy reasons, in looking through
the code, use as a fleet probably causes corrupt data because every worker
would generated it's own local root CA (making the API not work as intended).

This API is not used for anything in current Nova code. It makes Nova a
certificate authority for random 3rd party use (which it really should not be).
There is no managing of entropy, so aggressive use of this API can have
negative impacts on the entropy of your cloud depending on where your workers
are.

Nova-cert is an instance of Nova doing a non essential thing badly. Doing
security related operations badly is worse than not doing them at all.

Use Cases
---------

None

Proposed change
===============

``nova-cert`` has been deprecated since July 2016 with the commit [1] that
added release note and logged a warning stating ``nova-cert`` is deprecated.
If the deprecation cycle allows, dropping ``nova-cert`` should be
straightforward.

Alternatives
------------

Alternative approach is to not change anything, letting ``nova-cert`` be.

Data model impact
-----------------

None

REST API impact
---------------

Return `410 Gone` upon calling

* ``POST /os-certificates``
* ``GET /os-certificates/root``

Additionally, exception stating that feature is not available anymore should
be raised and logged.

Security impact
---------------

This change will affect the possibility to generate certificates in a safe
manner. Virtual machines tend to not have a lot of entropy thus limiting the
level of random numbers available from pseudorandom number generator to the
Linux kernel. There are additional packages that users would have to install
inside virtual machines to increase entropy when generating certificates
inside them.

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

We remove the need to run and manage ``nova-cert`` process, which gives us
one less service that need to be monitored and have HA explored.

Developer impact
----------------

ec2-api will become broken [2] after we remove ``nova-cert`` service

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Maciej Szankin (macsz)

Other contributors:
  OSIC

Work Items
----------


* remove ``nova-cert`` starter script
* remove tests
* delete ``nova-cert`` service

Dependencies
============

None

Testing
=======

Tempest [3] will require updating to adjust to this change.

Documentation Impact
====================

Update admin guide to reflect these changes.

References
==========

[1] https://github.com/openstack/nova/commit/789edad0e811d866551bec18dc7729541105f59d
[2] https://github.com/openstack/ec2-api/blob/480dc02de0d8413aa518a23b22a0140013df1350/ec2api/clients.py#L140
[3] https://github.com/openstack/tempest/blob/8c8943aa45d0a6428fdd4e32aa4e3bd71f39d050/tempest/api/compute/certificates/test_certificates.py

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
