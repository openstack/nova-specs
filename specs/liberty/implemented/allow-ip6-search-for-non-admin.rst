..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Allow ip6 server search for non-admin
=====================================

https://blueprints.launchpad.net/nova/+spec/allow-ip6-search-for-non-admin

Add ``ip6`` to the list of options that are allowed for non-admins when
listing servers.


Problem description
===================

Filtering by IPv6 address is currently only allowed for admins, but there
is no reason to treat this differently than IPv4. It is also quite surprising
for a user to find that ``nova list --ip6 xxx`` will list all servers.

Use Cases
---------

A user will want to list servers based on their IPv6 address, just like they
can already do based on IPv4.

Project Priority
----------------

None

Proposed change
===============

Add a new API microversion for which the ``ip6`` option will no longer be
filtered out from the server search for non-admins.

Alternatives
------------

Treat the bug fix as a minor patch that will not require a new API
microversion. However in the conversation about the fix (see References)
there seemed to be consensus that a microversion is needed in order for
a client to be able to tell whether filtering by IPv6 is available or not.

Data model impact
-----------------

None

REST API impact
---------------

The new API is added as a microversion.

Request::

    GET /servers?ip6=<regex>

The request and response headers, body and possible codes are unchanged from
current behaviour. The ``ip6`` option will no longer be silently discarded
for non-admins.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

python-novaclient will have to be updated so that it can request the new
microversion when the ``--ip6`` option is used.

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
  Jens Rosenboom <j.rosenboom@x-ion.de>

Work Items
----------

* Add a new microversion and change
  ``nova/api/openstack/compute/plugins/v3/servers.py`` to add ``ip6`` to the
  list of allowed server search options.

Dependencies
============

None


Testing
=======

* Unit tests and API samples functional tests in the nova tree will be added.


Documentation Impact
====================

The nova/api/openstack/rest_api_version_history.rst document will be updated.


References
==========

[1] Originally reported as a bug: https://bugs.launchpad.net/nova/+bug/1450859

[2] ML thread discussing whether a microversion is needed:
  http://lists.openstack.org/pipermail/openstack-dev/2015-May/065118.html

[3] Proof of concept code change: https://review.openstack.org/179569
