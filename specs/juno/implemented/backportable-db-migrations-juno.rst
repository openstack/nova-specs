..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Allow DB migration backports to Icehouse
==========================================

https://blueprints.launchpad.net/nova/+spec/backportable-db-migrations-juno

Just as we did at the beginning of the Havana and Icehouse dev cycles, we need
to reserve a range of DB migrations as the first DB change in Juno. This will
allow a range to be used for migration backports to Icehouse if needed.


Problem description
===================

Normally, it is not possible to backport a change that requires a database
migration due to the linear versioned nature of the migrations.  For the last
two releases (Havana and Icehouse), we have reserved a set of empty migrations
as placeholders to allow for migration backports if needed.


Proposed change
===============

The proposed change is to reserve 10 migrations for Icehouse backports. These
migrations would be no-ops and would simply result in an increment of the
schema version.

Alternatives
------------

When figuring out ways to allow database migrations, alternatives usually
involve discussion of drastic changes to the way we manage migrations.  For
example, it could require moving to a new framework.  This proposal works for
our current use of sqlalchemy-migrate.  This will also be the third release
we've used this approach, so it's fairly well understood at this point.

Data model impact
-----------------

There's no changes to the data model as a part of this effort.  It simply gives
us the ability to backport data model changes to Icehouse.

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

These migrations have minimal cost and can be run against a database without
taking down Nova services.

Other deployer impact
---------------------

This set of changes requires doing database migrations.  However, they can be
done without any Nova downtime.

Developer impact
----------------

This must be the first set of migrations merged into Juno, or it doesn't work.

Developers must also be very careful when writing migrations that may be
backported.  They must be idempotent.  For example, if migration 115 is
backported to 107 in the previous release, someone who has executed the
backported migration must not suffer any trouble when the migration runs again
after an upgrade.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  russellb

Work Items
----------

* Create 10 placeholder migrations.


Dependencies
============

None


Testing
=======

The existing unit tests will cover this.  Both the normal devstack based CI
systems, as well as the "turbo-hipster" DB CI system will provide functional
test coverage of these placeholder migrations.


Documentation Impact
====================

None.


References
==========

* https://blueprints.launchpad.net/nova/+spec/backportable-db-migrations-icehouse

* https://blueprints.launchpad.net/nova/+spec/backportable-db-migrations

* http://lists.openstack.org/pipermail/openstack-dev/2013-March/006827.html
