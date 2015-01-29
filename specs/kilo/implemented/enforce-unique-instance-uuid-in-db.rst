..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Enforce unique instance uuid in data model
==========================================

https://blueprints.launchpad.net/nova/+spec/enforce-unique-instance-uuid-in-db

The instances.uuid column in the data model is not unique but by definition a
UUID should be unique, and given how it's used within nova and across other
openstack services like glance, neutron, ceilometer, etc, it should be unique.

Furthermore, there are Foreign Keys created against instances.uuid so it should
be unique.


Problem description
===================

* Uniqueness for instances.uuid is not enforced in the data model.

* There are foreign keys created on the instances.uuid column so it should be
  unique.

Use Cases
----------

As a DB2 user (deployer), I'd like to have the same foreign key constraints
with my DB2 Nova schema as MySQL and PostgreSQL.

Project Priority
-----------------

None, however, this is required for DB2 support in Nova.


Proposed change
===============

Add a database migration that checks for existing records where the
instances.uuid or related instance_uuid column is NULL and if found, fails the
migration until those are deleted.

A tool will be provided to scan the database for these records and list them,
then prompt the user to delete them.  A --force option could also be provided
in the tool to ignore any prompts and just delete the records if found.

The new migration would be blocked until the records are deleted.  Once there
are no records left, the migration will make those columns non-nullable via
SQLAlchemy and create a UniqueConstraint on the instances.uuid column.

Note that the fixed_ips table is the exception here since it can, by design,
contain NULL instance_uuid records to indicate deallocated and disassociated
fixed IPs.

Alternatives
------------

Do nothing and leave the nova objects layer to enforce unique instance uuid
entries, but this does not help with the foreign key issue in the data model.

Data model impact
-----------------

#. NULL instances.uuid/instance_uuid records must be deleted, except in table
   fixed_ips as described above.
#. The instances.uuid column will be made non-nullable.
#. A UniqueConstraint will be created on the instances.uuid column.

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

The main impacts to deployers are:

#. The biggest impact is the new migration. Migrations are potentially slow and
   require the controller service to be down when run.
#. The hope is that existing deployments are not carrying records where
   instances.uuid or instance_uuid are None so the NULL queries in the new
   migration script would not yield large result sets. However, the impact to
   the deployer here is that they would be forced to manually prune those
   records before the migration can continue. Note that it's expected that
   those cases are exceptional and they are only the result of an inconsistent
   database. So finding these records is not expected, but if it is a problem
   the migration will fail clearly with instructions on how to fix the problem.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mriedem@us.ibm.com

Work Items
----------

#. Add a new migration to make instances.uuid non-nullable and put a unique
   constraint on that column.
#. Write a tool to check for null instance_uuid records within the database
   for operators to use before the actual migration.

See the WIP patch for details: https://review.openstack.org/#/c/97946/


Dependencies
============

None.


Testing
=======

* Unit tests for the new database migration will be added to stub a database
  with NULL instance_uuid records to make sure the migration fails when those
  records are found and then test that when they are removed, the migration
  completes successfully and the unique constraint is created. Similarly the
  downgrade path will be unit tested.
* Unit tests will also be written for the scan tool used to run outside of the
  actual database migrations. This will mock out the backend database but will
  be used to test the CLI and logic.
* It is expected that turbo-hipster will cover scale testing the new migration
  for MySQL.


Documentation Impact
====================

None.


References
==========

* Work in progress nova patch: https://review.openstack.org/#/c/97946/

* Mailing list thread on making instances.uuid non-nullable:
  http://lists.openstack.org/pipermail/openstack-dev/2014-March/029467.html
