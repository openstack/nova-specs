..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Add Support for DB2 (v10.5+)
============================

https://blueprints.launchpad.net/nova/+spec/db2-database

The community currently supports MySQL and PostgreSQL production databases.
Several other integrated projects already support DB2. This blueprint adds
support to Nova for DB2 as a production database.


Problem description
===================

* Currently there is no support in the community for a deployer to run Nova
  against a DB2 backend database.

* For anyone running applications against an existing DB2 database that wants
  to move to OpenStack, they'd have to use a different database engine to
  run Nova in OpenStack.

* There is currently an inconsistent support matrix across the core projects
  since the majority of core projects support DB2 but Nova does not yet.

Use Cases
---------

As a deployer, I want to run Nova against a DB2 backend database so I can use
a single DB2 database engine for multiple integrated OpenStack services.

Project Priority
----------------

None, however, most of the other integrated projects in OpenStack already
support a DB2 backend database or are working toward that.

The integrated projects that currently support DB2 today:

  * Ceilometer
  * Cinder
  * Glance
  * Heat
  * Keystone
  * Neutron

The integrated projects that do not yet have DB2 support:

  * Ironic
  * Sahara
  * Trove

Also, oslo.db has DB2 support.


Proposed change
===============

Add code to support migrating the Nova database against a DB2 backend. This
would require a fresh deployment of Nova since there are no plans to migrate
an existing Nova database from another engine, e.g. MySQL to DB2.

Unit test code would also be updated to support running tests against a DB2
backend with the ibm_db_sa driver and all Nova patches will be tested against a
Tempest full run with 3rd party CI running DB2 that IBM will maintain.

There is already some code in Oslo's db.api layer to support common function
with DB2 like duplicate entry error handling and connection trace, so that is
not part of this spec.

Alternatives
------------

Deployers can use other supported database backends like MySQL or PostgreSQL,
but this may not be an ideal option for customers already running applications
with DB2 that want to integrate with OpenStack. In addition, you could run
other core projects with multiple schemas in a single DB2 OpenStack database,
but you'd have to run Nova separately which is a maintenance/configuration
problem.

Data model impact
-----------------

#. The 216 migration will be updated to handle conditions with DB2 like index
   and foreign key creation. The main issue here is that DB2 does not support
   unique constraints over nullable columns, it will instead create a unique
   index that excludes null keys. Most unique constraints created in Nova are
   on non-nullable columns, but the instances.uuid column is nullable and the
   216 migration creates a unique index on it, but this will not allow any
   foreign keys on the instances.uuid column to be created with DB2 since the
   reference column has to be a unique or primary key constraint.
#. In order to support creating the same foreign keys that reference the
   instances.uuid column as other database engines, the instances.uuid column
   must be made non-nullable and a unique constraint must be created on it.
   The dependent blueprint "Enforce unique instance uuid in data model" is
   used to handle this change.
#. Finally, add another migration script which creates the previously excluded
   foreign keys from the 216 migration script for DB2.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

The only performance impact on existing deployments is in the migration
script changes which would be tested with turbo-hipster.

Other deployer impact
---------------------

The new database migration which creates the missing foreign keys since the
control node needs to be down when running the migration. However, the new
migration only creates foreign keys if the backend is DB2, which would be a new
installation as noted in the `Proposed change`_ section so the impact should be
minimal.

Developer impact
----------------

The only impact on developers is if they are adding DB API code or migrations
that do not work with DB2 they will have to adjust those appropriately, just
like we do today with MySQL and PostgreSQL. IBM active technical contributors
would provide support/guidance on issues like this which require specific
conditions for DB2, although for the most part the DB2 InfoCenter provides
adequate detail on how to work with the engine and provides details on error
codes.

* DB2 SQL error message explanations can be found here:
  http://pic.dhe.ibm.com/infocenter/db2luw/v10r5/index.jsp?topic=%2Fcom.ibm.db2.luw.messages.sql.doc%2Fdoc%2Frsqlmsg.html

* Information on developing with DB2 using python can be found here:
  http://pic.dhe.ibm.com/infocenter/db2luw/v10r5/index.jsp?topic=%2Fcom.ibm.swg.im.dbclient.python.doc%2Fdoc%2Fc0054366.html

* Main contacts for DB2 questions in OpenStack:

   * Matt Riedemann (mriedem@us.ibm.com) - Nova core member
   * Brant Knudson (bknudson@us.ibm.com) - Keystone core member
   * Jay Bryant (jsbryant@us.ibm.com) - Cinder core member
   * Rahul Priyadarshi (rahul.priyadarshi@in.ibm.com) - ibm_db_sa maintainer

* The DB2 CI wiki page also provides contact information for issues with third
  party testing failures:
  https://wiki.openstack.org/wiki/IBM/DB2-TEST


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mriedem@us.ibm.com

Work Items
----------

#. Change the 216 migration to work with DB2.
#. Add a new migration to create the excluded foreign keys from the 216 script
   for DB2.
#. Make the test_migrations.py module work with a configured DB2 backend for
   running unit tests.

See the WIP patch for details: https://review.openstack.org/#/c/69047/


Dependencies
============

* Blueprint "Enforce unique instance uuid in data model" (completed in Kilo):
  https://blueprints.launchpad.net/nova/+spec/enforce-unique-instance-uuid-in-db

* DB2 10.5 support was added to sqlalchemy-migrate 0.9 during Icehouse:
  https://blueprints.launchpad.net/sqlalchemy-migrate/+spec/add-db2-support

* There are no requirements changes in Nova for the unit tests to work. The
  runtime requirements are the ibm-db-sa and ibm_db modules, which are both
  available from pypi. sqlalchemy-migrate optionally imports ibm-db-sa. The
  ibm-db-sa module requires a natively compiled ibm_db which has the c binding
  that talks to the DB2 ODBC/CLI driver.

* Note that only DB2 10.5+ is supported since that's what added unique index
  support over nullable columns which is how sqlalchemy-migrate handles unique
  constraints over nullable columns.


Testing
=======

There are three types of testing requirements, Tempest, unit test and
turbo-hipster performance/scale tests. Each have different timelines for when
they are proposed to be implemented.

* IBM is already running 3rd party CI for DB2 on the existing Nova WIP patch
  that adds DB2 support. The same 3rd party CI is running against all
  sqlalchemy-migrate changes with DB2 on py26/py27 and runs Tempest against
  Keystone/Glance/Cinder/Heat/Neutron patches with a DB2 backend. Once the DB2
  support is merged the DB2 3rd party CI would run against all Nova patches
  with a full Tempest run. This is considered required testing for this
  blueprint to merge in the Kilo release.

* While code will be added to make the Nova unit tests work against a DB2
  backend, running Nova unit tests against DB2 with third party CI is not
  considered in the scope of this blueprint for Kilo, but long-term this is
  something IBM wants to get running for additional QA coverage for DB2 in
  Nova. This is something that would be worked on after getting Tempest
  running. The plan for delivering third party unit test coverage is in the
  2015.2 'L' release.

* Running 3rd party turbo-hipster CI against DB2 is not in plan for this
  blueprint in Kilo but like running unit tests against DB2 in 3rd party CI,
  running turbo-hipster against DB2 in 3rd party CI would be a long-term goal
  for QA and the IBM team will work on that after Tempest is running and after
  unit test CI is worked on. The plan for delivering third party turbo-hipster
  performance test coverage is in the 2015.2 'L' release.

* The proposed penalty for failing to deliver third party unit test and/or
  turbo-hipster performance test coverage in the L release is that the Nova
  team will turn off voting/reporting of DB2 third party CI and not allow DB2
  fixes to Nova until the third party CI is available.

* More discussion in the mailing list here:
  http://lists.openstack.org/pipermail/openstack-dev/2014-May/035009.html


Documentation Impact
====================

* The install guides in the community do not go into specifics about setting up
  the database.  The RHEL/Fedora install guide says to use the openstack-db
  script provided by openstack-utils in RDO which uses MySQL.  The other
  install guides just say that SQLite3, MySQL and PostgreSQL are widely used
  databases. So for the install guides, those generic statements about
  supported databases would be updated to add DB2 to the list. Similar generic
  statements are also made in the following places which would be updated as
  well:

   * http://docs.openstack.org/training-guides/content/developer-getting-started.html
   * http://docs.openstack.org/admin-guide-cloud/compute.html
   * http://docs.openstack.org/trunk/openstack-ops/content/cloud_controller_design.html

* There are database topics in the security guide, chapters 32-34, so there
  would be DB2 considerations there as well, specifically:

   * http://docs.openstack.org/security-guide/content/ch041_database-backend-considerations.html
   * http://docs.openstack.org/security-guide/content/ch042_database-overview.html
   * http://docs.openstack.org/security-guide/content/ch043_database-transport-security.html


References
==========

* Work in progress nova patch: https://review.openstack.org/#/c/69047/

* "Enforce unique instance uuid in data model" spec:
  http://specs.openstack.org/openstack/nova-specs/specs/kilo/approved/enforce-unique-instance-uuid-in-db.html

* There are Chef cookbooks on stackforge which support configuring OpenStack
  to run with an existing DB2 installation:
  http://git.openstack.org/cgit/stackforge/cookbook-openstack-common/

* Mailing list thread on third party testing:
  http://lists.openstack.org/pipermail/openstack-dev/2014-May/035009.html

* DB2 10.5 InfoCenter: http://pic.dhe.ibm.com/infocenter/db2luw/v10r5/index.jsp

* Some older manual setup instructions for DB2 with OpenStack:
  http://www.ibm.com/developerworks/cloud/library/cl-openstackdb2/index.html

* ibm-db-sa: https://code.google.com/p/ibm-db/source/clones?repo=ibm-db-sa

* DB2 Third Party CI Wiki: https://wiki.openstack.org/wiki/IBM/DB2-TEST
